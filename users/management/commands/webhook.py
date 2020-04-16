import logging

import requests
from django.core.management.base import BaseCommand

from dice_time.settings import ORIGIN, API_TOKEN, LOCAL
from users.bot import bot

from users.tools import log_setup

logger = logging.getLogger('Dice')
# log_setup(logging.DEBUG)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true')

    def handle(self, **options):
        wh = bot.get_webhook_info()
        if wh.url:
            logger.info(f'Stop webhook {wh.url}')
            bot.delete_webhook()
        if wh.pending_update_count:
            bot.skip_updates()
        if 'delete' in options:
            return
        logger.info('Start webhook')
        bot.set_webhook(ORIGIN + 'tg/' + API_TOKEN)
