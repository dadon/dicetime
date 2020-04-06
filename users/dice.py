from telebot import apihelper, TeleBot
from telebot.apihelper import _convert_markup
from telebot.types import Message


class DiceMessage(Message):

    def __init__(self, *args):
        super().__init__(*args)
        self.dice_value = self.json['dice']['value']


class DiceBot(TeleBot):

    def send_dice(self, chat_id, disable_notification=False, reply_to_message_id=None, reply_markup=None):
        message = apihelper._make_request(self.token, 'sendDice', params={
            'chat_id': chat_id,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': _convert_markup(reply_markup)
        })
        return DiceMessage.de_json(message)

    # def send_message(self, chatone, disable_notification=None, timeout=None):_id, text, disable_web_page_preview=None, reply_to_message_id=None, reply_markup=None,
    #     #                  parse_mode=N