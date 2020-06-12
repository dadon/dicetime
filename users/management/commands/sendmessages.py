import logging
from time import sleep

import shortuuid
from django.core.management.base import BaseCommand
from pyrogram import Client, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError

from dice_time.settings import ADMIN_TG_IDS, TG_API_ID, TG_API_HASH, API_TOKEN
from dicebot.bot.markup import kb_home

from users.models import User

logger = logging.getLogger('Dice')


MESSAGE = '''
promo text
'''
BTN_MSG = 'Call to action'


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true')
        parser.add_argument('--chat-test', action='store_true')

    def handle(self, **options):
        with Client('pyrosession', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as app:
            logger.info('Start send messages')

            count_error = 0
            count_success = 0
            chats = []
            users = []

            if options['test']:
                users = User.objects.filter(id__in=ADMIN_TG_IDS)
            elif options['chat-test']:
                chats = [-1001466080283]
            else:
                users = User.objects.all()

            if chats:
                for chat_id in chats:
                    rand_str, room_id = shortuuid.uuid().lower()[:8], f'chat{chat_id}'
                    fs_url = f'https://friendoscope.com/{rand_str}/{room_id}'
                    markup = InlineKeyboardMarkup([[InlineKeyboardButton(BTN_MSG, url=fs_url)]])
                    try:
                        app.send_message(chat_id, MESSAGE, reply_markup=markup)
                        count_success += 1
                    except FloodWait as exc:
                        sleep(exc.x)
                        app.send_message(chat_id, MESSAGE, reply_markup=markup)
                        count_success += 1
                    except RPCError as exc:
                        logger.info(chat_id)
                        logger.info('###############')
                        logger.info(f'\n\n{type(exc)}: {exc}\n\n')
                        count_error += 1

            if users:
                user_map = {u.id: u for u in users}

                for uid, user in user_map.items():
                    try:
                        app.send_message(
                            uid, MESSAGE, disable_web_page_preview=True, reply_markup=kb_home(user))
                        count_success += 1
                    except FloodWait as exc:
                        sleep(exc.x)
                        app.send_message(
                            uid, MESSAGE, disable_web_page_preview=True, reply_markup=kb_home(user))
                        count_success += 1
                    except RPCError as exc:
                        logger.info(user)
                        logger.info('###############')
                        logger.info(f'\n\n{type(exc)}: {exc}\n\n')
                        count_error += 1
            logger.info(f'Done. count_success={count_success} count_error={count_error}')
