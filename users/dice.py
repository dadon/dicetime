from datetime import datetime

from telebot import apihelper, TeleBot
from telebot.apihelper import _convert_markup
from telebot.types import Message


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
