import logging
from time import sleep

from django.core.management.base import BaseCommand
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

from dice_time.settings import ADMIN_TG_IDS, TG_API_ID, TG_API_HASH, API_TOKEN

from users.models import User

logger = logging.getLogger('Dice')


MESSAGE = '''
Привет! 

Началось голосование за лучший проект хакатона и ваш покорный номинирован. 

Поддержите своим голосом, если я вам понравился: https://minterscan.net/vote

Если уделаем всех этих неудачников на голосовании, то завтра отпразнуем - буду выдавать награду в два раза выше чем была сегодня 😎
'''


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true')

    def handle(self, **options):
        with Client('pyrosession', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as app:
            logger.info('Start send messages')

            if options['test']:
                users = User.objects.filter(id__in=ADMIN_TG_IDS)
            else:
                users = User.objects.all()

            user_map = {u.id: u for u in users}
            count_error = 0
            count_success = 0
            for uid, user in user_map.items():
                try:
                    app.send_message(
                        uid, MESSAGE, disable_web_page_preview=True, reply_markup=user.home_markup)
                    count_success += 1
                except FloodWait as exc:
                    sleep(exc.x)
                    app.send_message(
                        uid, MESSAGE, disable_web_page_preview=True, reply_markup=user.home_markup)
                    count_success += 1
                except RPCError as exc:
                    logger.info(user)
                    logger.info('###############')
                    logger.info(f'\n\n{type(exc)}: {exc}\n\n')
                    count_error += 1
            logger.info(f'Done. count_success={count_success} count_error={count_error}')
