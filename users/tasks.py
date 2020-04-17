import logging

from telebot import types

from celery_app import app
from users.bot import bot

logger = logging.getLogger('Dice')


@app.task
def tg_webhook_task(payload, pending_updates_skip_until):
    logger.debug(f'Update: {payload}')
    update = types.Update.de_json(payload)
    if update.message and update.message.date <= pending_updates_skip_until:
        logger.info(f'#### Skipping this update')
        return
    bot.process_new_updates([update])
