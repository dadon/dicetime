import logging
from datetime import datetime
from time import sleep

from pyrogram.api.functions.channels import GetFullChannel
from pyrogram.api.functions.messages import GetFullChat
from pyrogram.api.types import InputPeerChannel, InputPeerChat
from telebot import apihelper, TeleBot
from telebot.apihelper import _convert_markup, ApiException
from telebot.types import Message

from pyrogram import Client

from dice_time.settings import API_TOKEN, TG_API_ID, TG_API_HASH
from users.misc import retry

logger = logging.getLogger('Dice')


def get_fullchat(app, chat_id):
    peer = app.resolve_peer(chat_id)
    if isinstance(peer, InputPeerChannel):
        return app.send(GetFullChannel(channel=peer))
    if isinstance(peer, InputPeerChat):
        return app.send(GetFullChat(chat_id=peer.chat_id))


def _chat_date(app, chat, chat_id):
    chat_date = None
    if not chat.megagroup:
        chat_date = chat.date
        logger.info(f'####### Got chat date (GetFullChat) {chat_date}')
    else:

        messages = filter(
            lambda m: not m.empty,
            app.get_messages(chat_id, range(1, 201), replies=0))
        for msg in messages:
            chat_date = msg.date
            logger.info(f'####### Got chat date (fullchat + get_messages) {chat_date}')
            break
    return chat_date


@retry(Exception, tries=5, delay=0.5, backoff=1)
def get_chat_creation_date(chat_id):
    with Client('pyrosession', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as app:
        chat_date = None
        full = get_fullchat(app, chat_id)
        if len(full.chats) == 1:
            chat = full.chats[0]
            chat_date = _chat_date(app, chat, chat_id)
        else:
            for chat in full.chats:
                if chat.broadcast:
                    continue
                chat_date = _chat_date(app, chat, chat_id)
                break

        if chat_date is None:
            raise Exception(f"Can't get chat date\n{str(full)}")

        return chat_date


def get_chatmember_joined_date(user, chat):
    if user.id == chat.creator.id:
        return chat.created_at

    with Client('pyrosession', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as app:
        chatmember = app.get_chat_member(chat.chat_id, user.id)
        return datetime.utcfromtimestamp(chatmember.joined_date) if chatmember.joined_date else None


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
                if result['error_code'] in [400, 403]:
                    logger.info(f'{result["error_code"]}: skipping')
                    return result['error_code']
                if result['error_code'] == 429:
                    logger.info(f'429 error. Sleeping {result["parameters"]["retry_after"]}')
                    sleep(result['parameters']['retry_after'])
                else:
                    logger.info('Other error. Sleeping 1 sec.')
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
