import logging
import time
from datetime import datetime

from telebot import apihelper, TeleBot
from telebot.apihelper import _convert_markup, ApiException
from telebot.types import Message


logger = logging.getLogger('Dice')


class DiceMessage(Message):

    def __init__(self, *args):
        super().__init__(*args)
        self.dice_value = self.json['dice']['value']


class DiceBot(TeleBot):

    def __init__(self, *args, **kwargs):
        self.start_time = datetime.utcnow().timestamp()
        super().__init__(*args, **kwargs)

    def send_dice(self, chat_id, disable_notification=False, reply_to_message_id=None, reply_markup=None):
        message = apihelper._make_request(self.token, 'sendDice', params={
            'chat_id': chat_id,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': _convert_markup(reply_markup)
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
                super().send_message(*args, **kwargs)
                return
            except ApiException as api_exc:
                result = api_exc.result
                result = result.json()
                logger.info(result)
                if result['error_code'] == 429:
                    logger.info('429 error. sleeping')
                    time.sleep(result['parameters']['retry_after'])
                else:
                    time.sleep(1)
