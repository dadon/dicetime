import logging

from django.core.management.base import BaseCommand

from users.tools import log_setup

logger = logging.getLogger('Dice')
log_setup(logging.DEBUG)


class Command(BaseCommand):
    def handle(self, **options):
        from users.bot import bot
        logger.info('Start polling')
        wh_info = bot.get_webhook_info()
        if wh_info.url:
            bot.delete_webhook()
        bot.polling(none_stop=True, interval=0, timeout=5)
