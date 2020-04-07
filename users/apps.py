import logging
import sys

from django.apps import AppConfig
from dice_time.settings import LOCAL, ORIGIN, API_TOKEN

logger = logging.getLogger()


def bot_run():
    from users.bot import bot

    if LOCAL:
        logger.info('---------- called')
        bot.delete_webhook()
        bot.polling(none_stop=True, interval=0)
    else:
        wh = bot.get_webhook_info()
        if wh.pending_update_count:
            bot.delete_webhook()
            bot.skip_updates()
        bot.set_webhook(ORIGIN + 'tg/' + API_TOKEN)


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        if not 'manage.py' in sys.argv or 'runserver' in sys.argv:
            from . import scheduler
            scheduler.scheduler.add_job(bot_run)
            scheduler.start()
