import logging
from datetime import datetime
from time import time, sleep

from pyrogram.api.functions.messages import GetChats
from telebot import apihelper, TeleBot
from telebot.apihelper import _convert_markup, ApiException
from telebot.types import Message

from pyrogram import Client

from dice_time.settings import API_TOKEN, TG_API_ID, TG_API_HASH
from users.tools import retry

logger = logging.getLogger('Dice')


@retry(Exception, tries=5, delay=0.5, backoff=1)
def get_chat_creation_date(chat_id):
    with Client(':memory:', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as app:
        try:
            response = app.send(GetChats(id=[abs(chat_id)]))
            chat_date = response.chats[0].date
            logger.info(f'####### Got chat date (GetChats) {chat_date}')
            return chat_date
        except Exception as exc:
            logger.debug(exc)
            message = app.get_messages(chat_id, 1)
            if message.empty:
                raise Exception('History invisible')
            chat_date = message.date
            logger.info(f'####### Got chat date (get_messages) {chat_date}')
            return chat_date


class DiceMessage(Message):

    def __init__(self, *args):
        super().__init__(*args)
        self.dice_value = self.json['dice']['value']


class DiceBot(TeleBot):

    def __init__(self, *args, **kwargs):
        super(DiceBot, self).__init__(*args, **kwargs)
        now = datetime.utcnow()
        self.start_time = now.timestamp()
        self._user = None

    @property
    def user(self):
        if not self._user:
            self._user = self.get_me()
        return self._user

    def send_dice(self, chat_id, disable_notification=False, reply_to_message_id=None, reply_markup=None):
        message = apihelper._make_request(self.token, 'sendDice', params={
            'chat_id': chat_id,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': _convert_markup(reply_markup),
            'connect-timeout': -9.5
        })
        return DiceMessage.de_json(message)

    def skip_updates(self):
        total = 0
        updates = self.get_updates(offset=self.last_update_id, timeout=1)
        while updates:
            total += len(updates)
            for update in updates:
                if update.update_id > self.last_update_id:
                    self.last_update_id = update.update_id
            updates = self.get_updates(offset=self.last_update_id + 1, timeout=1)
        return total

    def send_message(self, *args, **kwargs):
        for i in range(3):
            try:
                return super(DiceBot, self).send_message(*args, timeout=-9.5, **kwargs)
            except ApiException as api_exc:
                result = api_exc.result
                result = result.json()
                logger.info(result)
                if result['error_code'] == 429:
                    logger.info('429 error. sleeping')
                    sleep(result['parameters']['retry_after'])
                else:
                    sleep(1)

    def get_updates(self, *args, **kwargs):
        for i in range(3):
            try:
                return super(DiceBot, self).get_updates(*args, **kwargs)
            except Exception as api_exc:
                if isinstance(api_exc, ApiException):
                    result = api_exc.result
                    result = result.json()
                    logger.debug(result)
                else:
                    logger.debug(api_exc)
                sleep(0.1)
        return []
