from pyrogram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from users.models import Text

RULES_BTN_RU = Text.objects.get(name='kb-home-rules').text_ru
WALLET_BTN_RU = Text.objects.get(name='kb-home-wallet').text_ru
RULES_BTN_EN = Text.objects.get(name='kb-home-rules').text_eng
WALLET_BTN_EN = Text.objects.get(name='kb-home-wallet').text_eng
CHAT_ADMIN_RU = Text.objects.get(name='kb-home-admin').text_ru
CHAT_ADMIN_EN = Text.objects.get(name='kb-home-admin').text_eng

KB_HOME_RU = [[RULES_BTN_RU, WALLET_BTN_RU], [CHAT_ADMIN_RU]]
KB_HOME_EN = [[RULES_BTN_EN, WALLET_BTN_EN], [CHAT_ADMIN_EN]]
KB_REMOVE = ReplyKeyboardRemove()


def kb_home(user):
    kb = user.choice_localized(ru_obj=KB_HOME_RU, en_obj=KB_HOME_EN)
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


def markup_chat_actions(chat, btn_texts):
    u_limit_text = btn_texts['ulimit'].format(ulimit=chat.user_limit_day, coin=chat.coin)
    c_limit_text = btn_texts['climit'].format(climit=chat.chat_limit_day, coin=chat.coin)

    dice_time_text = btn_texts['dt'].format(
        dt_from=chat.dice_time_from.strftime("%H:%M"),
        dt_to=chat.dice_time_to.strftime("%H:%M"))
    back_text = btn_texts['back']
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(u_limit_text, callback_data=f'set.ulimit.{chat.chat_id}')],
        [InlineKeyboardButton(c_limit_text, callback_data=f'set.climit.{chat.chat_id}')],
        [InlineKeyboardButton(dice_time_text, callback_data=f'set.dt.{chat.chat_id}')],
        [InlineKeyboardButton(back_text, callback_data='set.back')]
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


def markup_tutorial(user, tutorial_name):
    step = user.tutorial[tutorial_name]['step']

    try:
        user.get_tutorial_text(tutorial_name, step=step+1)
        markup = [[InlineKeyboardButton('← Назад', callback_data=f'tutorial-{tutorial_name}-back'),
                   InlineKeyboardButton('« Продолжить »', callback_data=f'tutorial-{tutorial_name}-continue')]]
        if step == 1:
            markup = [[InlineKeyboardButton('« Продолжить »', callback_data=f'tutorial-{tutorial_name}-continue')]]

    except Exception:  # я не смог словить users.models.Text.DoesNotExist: Text matching query does not exist.
        markup = [[InlineKeyboardButton('← Назад', callback_data=f'tutorial-{tutorial_name}-back'),
                   InlineKeyboardButton('« Завершить »', callback_data=f'tutorial-{tutorial_name}-end')]]
        if step == 1:
            markup = [[InlineKeyboardButton('« Завершить »', callback_data=f'tutorial-{tutorial_name}-end')]]

    return InlineKeyboardMarkup(markup)
