import logging
from time import sleep

from django.core.management.base import BaseCommand

from dice_time.settings import ADMIN_TG_IDS
from users.bot import bot
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

        logger.info('Start send messages')

        if options['test']:
            users = User.objects.filter(id__in=ADMIN_TG_IDS)
        else:
            users = User.objects.all()

        uids = [u.id for u in users]
        count403 = 0
        count400 = 0
        count_success = 0
        for user_batch in [[uid for uid in uids[i: i + 30]] for i in range(0, len(uids), 30)]:
            for uid in user_batch:
                result = bot.send_message(uid, MESSAGE, disable_web_page_preview=True)
                if result == 403:
                    count403 += 1
                elif result == 400:
                    count400 += 1
                elif result:
                    count_success += 1
            sleep(1)
            logger.info(f'Sent batch. count403={count403} count_success={count_success}')
