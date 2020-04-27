import logging
from datetime import datetime
from time import sleep

from django.core.management.base import BaseCommand
from pyrogram import Client
from pyrogram.errors import ChannelInvalid, ChannelPrivate

from dice_time.settings import TG_API_HASH, API_TOKEN, TG_API_ID
from users.models import AllowedChat, ChatMember, User

logger = logging.getLogger('Dice')


def collect_chat_members(app, chat):
    try:
        return [m for m in app.iter_chat_members(chat.chat_id)]
    except (AttributeError, ChannelInvalid, ChannelPrivate) as exc:
        logger.info(f'Error for {chat.title_chat} ({chat.chat_id})')
        logger.info(exc)


def save_chat_members(members):
    logger.info('Start save chat members')
    users = User.objects.in_bulk()

    tg_users = {
        m.user.id: m.user
        for chat_members in members.values()
        for m in chat_members
    }
    inactive_users = [u for u in tg_users.values() if u.id not in users]
    new_users = [
        User(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username
        ) for user in inactive_users
    ]
    User.objects.bulk_create(new_users)
    users.update({u.id: u for u in new_users})
    logger.info(f'Created {len(new_users)} new users')

    ChatMember.objects.pg_bulk_update_or_create([
        {
            "chat": chat,
            "user": users[member.user.id],
            "joined_date": datetime.utcfromtimestamp(member.joined_date) if member.joined_date else chat.created_at
        }
        for chat, chat_members in members.items() for member in chat_members
    ], key_fields=('chat', 'user'), update=True)
    logger.info('Updated ChatMember table')


class Command(BaseCommand):

    def handle(self, **options):
        errored = 0
        success = 0
        all_members = {}
        logger.info('Start existing chat members join date collection')
        with Client('pyrosession', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as app:
            for chat in AllowedChat.objects.all():
                members = collect_chat_members(app, chat)
                sleep(1)
                if members is None:
                    errored += 1
                    continue
                success += 1
                all_members[chat] = members

            logging.info(f'Collected {sum(len(mems) for mems in all_members.values())} chat member objects.')
            logging.info(f'Success chats: {success}\nErrored chats: {errored}')

        save_chat_members(all_members)

