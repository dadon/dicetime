import logging
from time import sleep

from django.core.management.base import BaseCommand
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError, ChannelInvalid, ChannelPrivate, PeerIdInvalid

from dice_time.settings import TG_API_ID, TG_API_HASH, API_TOKEN
from users.models import User

logger = logging.getLogger('Dice')


FS_PROMO_VIDEO = 'content/cube.mp4'
FS_PROMO_TEXT = '''
Привет! 

Появилась новая крутая игрушка c Minter монетой `CUBE`
Игра так и называется **-=Cube=-**

Регистрация через моего собутыльника - бота @CubeMinterBot

PS: Они там всем новым игрокам дают по 10 `CUBE`!
'''


def collect_chat_members(app: Client, chat_id, chat_title=None):
    try:
        return [m for m in app.iter_chat_members(chat_id)]
    except (AttributeError, ChannelInvalid, ChannelPrivate, PeerIdInvalid) as exc:
        logger.info(f'Error for chat {chat_title} ({chat_id})')
        logger.info(exc)
        return []


def broadcast_users(app, user_ids, text, doc=None):
    logger.info(f'Broadcast for {len(user_ids)} started.')
    count_success = 0
    count_error = 0
    success_uids = []
    file_id, file_ref = None, None
    for uid in user_ids:
        try:
            if doc:
                # app.send_video(uid, doc, caption=text)
                msg = app.send_document(uid, file_id or doc, file_ref=file_ref, caption=text)
                if not file_id:
                    file_id = msg.video.file_id
                if not file_ref:
                    file_ref = msg.video.file_ref
            else:
                app.send_message(uid, text)
            success_uids.append(uid)
            count_success += 1
        except FloodWait as exc:
            sleep(exc.x)
            app.send_message(uid, text)
            count_success += 1
        except RPCError as exc:
            logger.info(f'############### error for user {uid}')
            logger.info(f'\n\n{type(exc)}: {exc}\n\n')
            count_error += 1
    logger.info(f'Broadcast done. count_success={count_success} count_error={count_error}')
    return success_uids


def broadcast_chat_members(app, chat_ids, text):
    uids = set()
    for chat_id in chat_ids:
        members = collect_chat_members(app, chat_id=chat_id)
        uids.update(member.user.id for member in members)
        logger.info(f'Got {len(members)} members from chat {chat_id}. Potential recipients {len(uids)}')
    broadcast_users(app, uids, text)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--fchatlist')
        parser.add_argument('--uall', action='store_true')
        parser.add_argument('--utest', nargs='+')

    def handle(self, **options):
        with Client('pyrosession', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as app:
            chat_list_filename = options.get('fchatlist')
            uall = options.get('uall')
            utest = options.get('utest')
            print(utest)
            chat_ids = []
            user_ids = []

            if chat_list_filename:
                with open(chat_list_filename, 'r') as f:
                    for line in f:
                        chat_ids.append(int(line))

            if chat_ids:
                logger.info(f'Got {len(chat_ids)} chats')
                broadcast_chat_members(app, chat_ids, FS_PROMO_TEXT)
                return

            if uall:
                user_ids = [u.id for u in User.objects.all()]
            elif utest:
                user_ids = utest

            if user_ids:
                logger.info(f'Got {len(user_ids)} users')
                success_ids = broadcast_users(app, user_ids, FS_PROMO_TEXT, doc=FS_PROMO_VIDEO)
                logger.info('########## success ids ##########')
                logger.info('\n' + '\n'.join(success_ids))
                logger.info('########## success ids ##########')
                return
