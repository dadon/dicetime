import logging
import traceback

# from pyrogram import Client
# from pyrogram.api.functions.channels import GetFullChannel
# from pyrogram.api.functions.messages import GetFullChat
# from pyrogram.api.types import InputPeerChannel, InputPeerChat, ChannelFull, ChatFull
from telebot import types

from celery_app import app
# from dice_time.settings import TG_API_ID, TG_API_HASH, API_TOKEN
from .bot import bot

logger = logging.getLogger('Dice')


@app.task
def tg_webhook_task(payload, pending_updates_skip_until):
    try:
        update = types.Update.de_json(payload)
        if update.message and update.message.date <= pending_updates_skip_until:
            logger.info(f'#### Skipping this update')
            return
        logger.debug(f'Update: {payload}')
        bot.process_new_updates([update])
        logger.debug('-----------------')
    except Exception as exc:
        logger.error(f'{type(exc)}: {exc}')
        logger.error(traceback.format_exc())



#
#
# def get_history(app, chat_id):
#     full = get_fullchat(app, chat_id)
#     if isinstance(full.full_chat, ChatFull):
#         return
#
# @app.task
# def parse_message_history(chat_id):
#     with Client('pyrosession', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=token) as app:
#         current_offset = 1
#         app.get_messages(chat_id, range(current_offset, 201))
