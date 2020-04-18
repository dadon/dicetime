from telebot import types

KB_REMOVE = types.ReplyKeyboardRemove()

RULES_BTN_RU = '❔ Правила'
WALLET_BTN_RU = '💰 Мой Кошелёк'
RULES_BTN_EN = '❔ Rules'
WALLET_BTN_EN = '💰 My Wallet'
CHAT_ADMIN_RU = 'Управление чатами'
CHAT_ADMIN_EN = 'Chat administration'

CANCEL_INPUT_EN = 'Cancel'
CANCEL_INPUT_RU = 'Отмена'


HOME_MARKUP_RU = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
HOME_MARKUP_RU.add(RULES_BTN_RU, WALLET_BTN_RU, CHAT_ADMIN_RU)

HOME_MARKUP_ENG = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
HOME_MARKUP_ENG.add(RULES_BTN_EN, WALLET_BTN_EN, CHAT_ADMIN_EN)


def cancel_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(CANCEL_INPUT_RU, callback_data='back'))
    return markup


def wallet_markup(to_wallet_text=None, redeem_deeplink=None, timeloop_text=None, user_address=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if to_wallet_text and redeem_deeplink:
        markup.add(types.InlineKeyboardButton(to_wallet_text, url=redeem_deeplink))
    if timeloop_text:
        markup.add(types.InlineKeyboardButton(timeloop_text, callback_data=f'timeloop_{user_address or ""}'))

    return markup if len(markup.keyboard) else None


def another_chat_markup(bot_username, msg_text):
    url = f'https://telegram.me/{bot_username}?startgroup=hbase'
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(msg_text, url=url))
    return markup


def chat_list_markup(chats):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for chat in chats:
        markup.add(types.InlineKeyboardButton(f'{chat.title_chat}', callback_data=f'admin.{chat.chat_id}'))
    return markup


def chat_actions_markup(chat):
    markup = types.InlineKeyboardMarkup(row_width=1)
    u_limit_text = f'Лимит на юзера в день ({chat.user_limit_day} {chat.coin})'
    c_limit_text = f'Лимит на чат в день ({chat.chat_limit_day} {chat.coin})'
    dice_time_text = f'Dice Time ({chat.dice_time_from.strftime("%H:%M")} - {chat.dice_time_to.strftime("%H:%M")})'
    markup.add(
        types.InlineKeyboardButton(u_limit_text, callback_data=f'set.ulimit.{chat.chat_id}'),
        types.InlineKeyboardButton(c_limit_text, callback_data=f'set.climit.{chat.chat_id}'),
        types.InlineKeyboardButton(dice_time_text, callback_data=f'set.dt.{chat.chat_id}'),
        types.InlineKeyboardButton('Назад', callback_data='set.back'))
    return markup
