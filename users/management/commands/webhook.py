import logging
from datetime import datetime

import requests
from django.core.management.base import BaseCommand

from dice_time.settings import ORIGIN, API_TOKEN, LOCAL
from users.bot import bot
from users.models import Service

from users.tools import log_setup

logger = logging.getLogger('Dice')
# log_setup(logging.DEBUG)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true')
        parser.add_argument('--info', action='store_true')

    def handle(self, **options):
        wh = bot.get_webhook_info()
        logger.info(f'Webhook info: {wh}')
        if options['info']:
            return
        if wh.url:
            logger.info(f'Stop webhook {wh.url}')
            bot.delete_webhook()
        if options['delete']:
            return
        if wh.pending_update_count:
            now = datetime.utcnow()
            logger.info(f'Will skip updates until {now}')
            service, _ = Service.objects.get_or_create(pk=1)
            service.pending_updates_skip_until = now
            service.save()
        logger.info('Start webhook')
        bot.set_webhook(ORIGIN + 'tg2/' + API_TOKEN, max_connections=8)
