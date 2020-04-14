import logging

import requests
from django.core.management.base import BaseCommand

from dice_time.settings import ORIGIN, API_TOKEN, LOCAL
from users.bot import bot

from users.tools import log_setup

logger = logging.getLogger('Dice')
log_setup(logging.DEBUG)


class Command(BaseCommand):
    def handle(self, **options):
        wh = bot.get_webhook_info()
        if wh.pending_update_count:
            bot.delete_webhook()
            bot.skip_updates()
        logger.info('Start webhook')
        bot.set_webhook(ORIGIN + 'tg/' + API_TOKEN)
