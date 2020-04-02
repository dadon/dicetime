from telebot import apihelper, TeleBot
from telebot.apihelper import _convert_markup


class DiceBot(TeleBot):

    def send_dice(self, chat_id, disable_notification=False, reply_to_message_id=None, reply_markup=None):
        return apihelper._make_request(self.token, 'sendDice', params={
            'chat_id': chat_id,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': _convert_markup(reply_markup)
        })
