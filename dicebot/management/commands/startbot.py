import logging

from django.core.management.base import BaseCommand
from pyrogram import Client

from dice_time.settings import TG_API_ID, TG_API_HASH, API_TOKEN

logging.basicConfig(filename='test.log', level=logging.DEBUG)
logger = logging.getLogger('Dice')


class Command(BaseCommand):
    def handle(self, **options):
        logger.info('Start polling')
        app = Client(
            'pyrosession',
            api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN,
            plugins={'root': 'dicebot/bot'}, workers=8)
        app.run()
