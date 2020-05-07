from pyrogram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

RULES_BTN_RU = '❔ Правила'
WALLET_BTN_RU = '💰 Мой Кошелёк'
RULES_BTN_EN = '❔ Rules'
WALLET_BTN_EN = '💰 My Wallet'
CHAT_ADMIN_RU = 'Управление чатами'
CHAT_ADMIN_EN = 'Chat administration'
CANCEL_INPUT_EN = 'Cancel'
CANCEL_INPUT_RU = 'Отмена'

KB_HOME_RU = [[RULES_BTN_RU, WALLET_BTN_RU], [CHAT_ADMIN_RU]]
KB_HOME_EN = [[RULES_BTN_EN, WALLET_BTN_EN], [CHAT_ADMIN_EN]]


def kb_home(kb):
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def markup_wallet(to_wallet_text=None, redeem_deeplink=None, timeloop_text=None, user_address=None):
    kb = []
    if to_wallet_text and redeem_deeplink:
        kb.append([InlineKeyboardButton(to_wallet_text, url=redeem_deeplink)])
    if timeloop_text:
        kb.append([InlineKeyboardButton(timeloop_text, callback_data=f'timeloop_{user_address or ""}')])

    return InlineKeyboardMarkup(kb) if kb else None


def markup_chat_list(chats):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f'{chat.title_chat}', callback_data=f'admin.{chat.chat_id}')
    ] for chat in chats])


def markup_chat_actions(chat):
    u_limit_text = f'Лимит на юзера в день ({chat.user_limit_day} {chat.coin})'
    c_limit_text = f'Лимит на чат в день ({chat.chat_limit_day} {chat.coin})'
    dice_time_text = f'Dice Time ({chat.dice_time_from.strftime("%H:%M")} - {chat.dice_time_to.strftime("%H:%M")})'
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(u_limit_text, callback_data=f'set.ulimit.{chat.chat_id}')],
        [InlineKeyboardButton(c_limit_text, callback_data=f'set.climit.{chat.chat_id}')],
        [InlineKeyboardButton(dice_time_text, callback_data=f'set.dt.{chat.chat_id}')],
        [InlineKeyboardButton('Назад', callback_data='set.back')]
    ])
    return markup


def markup_add_to_chat(bot_username, btn_text):
    url = f'https://telegram.me/{bot_username}?startgroup=hbase'
    markup = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=url)]])
    return markup


def markup_take_money(bot_username, btn_text):
    url = f'https://telegram.me/{bot_username}'
    markup = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=url)]])
    return markup