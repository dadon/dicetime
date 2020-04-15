import logging
from datetime import datetime, date, timedelta
from decimal import getcontext, ROUND_DOWN
from functools import partial
from random import randint
from pprint import pformat

import requests
from django.db.models import Sum

from mintersdk.sdk.check import MinterCheck
from mintersdk.sdk.deeplink import MinterDeeplink
from mintersdk.sdk.transactions import MinterRedeemCheckTx, MinterSendCoinTx
from mintersdk.sdk.wallet import MinterWallet

from shortuuid import uuid
from telebot.types import CallbackQuery

from .dice import DiceBot, get_chat_creation_date
from .minter import send, API, wallet_balance
from .models import *
from dice_time.settings import API_TOKEN, LOCAL, RELEASE_UTC_DATETIME, ORIGIN

import time

from .markups import *

from django.conf import settings

from .utils import get_localized_choice, get_language

logger = logging.getLogger('Dice')

bot = DiceBot(API_TOKEN, skip_pending=True, threaded=False)


def get_user_timeloop_address(user_id):
    r = requests.get(f'https://timeloop.games/bot-status/{user_id}')
    if r.status_code != 200:
        return None
    return r.json().get('address')

# ---

def is_group_text(msg):
    return msg.chat.type != 'private' \
           and msg.text \
           and not msg.text.startswith('/') \
           and not msg.reply_to_message \
           and not msg.forward_from


def is_private_text(msg):
    return msg.chat.type == 'private' and msg.text


def is_group_text_reply(msg):
    return msg.chat.type in ('group', 'supergroup') and bool(msg.reply_to_message) and msg.text


def is_chat_admin_button(msg):
    return msg.chat.type == 'private' and msg.text in [CHAT_ADMIN_RU, CHAT_ADMIN_EN]
# ----


def get_chat_creator(chat_id):
    for member in bot.get_chat_administrators(chat_id):
        if member.status == 'creator':
            user_id = member.user.id
            if not User.objects.filter(pk=user_id).exists():
                user, _ = get_user_model(member.user)
                return user
            return User.objects.get(pk=user_id)


def send_message(chat_id, text, markup):
    chat_id = chat_id if isinstance(chat_id, int) else chat_id.chat.id
    bot.send_message(
        chat_id,
        text=text,
        parse_mode='markdown',
        reply_markup=markup,
        disable_web_page_preview=True
    )


def reply_to(message, text, markup):
    mes = bot.reply_to(message=message, text=text, reply_markup=markup,parse_mode='markdown')
    return mes

# ----


def get_user_model(tg_user):
    ru_lang = Language.objects.get(pk=1)
    en_lang = Language.objects.get(pk=2)
    user_lang = get_language(tg_user.language_code)
    user_lang_model = ru_lang if user_lang == 'ru' else en_lang

    user, is_created = User.objects.get_or_create(
        id=tg_user.id, defaults={
            'last_name': tg_user.last_name,
            'first_name': tg_user.first_name,
            'username': tg_user.username,
            'language': user_lang_model
        })

    if is_created:
        wallet = MinterWallet.create()
        MinterWallets.objects.get_or_create(
            user=user, defaults={
                'address': wallet['address'],
                'mnemonic': wallet['mnemonic']
            })

    # try change lang when user changes lang
    if not is_created and user.language != user_lang_model:
        user.language = user_lang_model
        user.save()
    return user, is_created


def set_unbond_obj(event):
    if not event.summa:
        return
    event.is_payed = True
    event.save()
    wallet_to = MinterWallets.objects.get(user=event.user).address
    coin = str(Tools.objects.get(pk=1).coin)
    Payment.objects.create(
        user=event.user,
        event=event,
        to=wallet_to,
        coin=coin,
        amount=event.summa)


def notify_win(user, event, coin):
    chat_id = user.id
    send_message(chat_id, f'Вы выиграли {event.summa} {coin}', None)
    event.is_notified = True
    event.save()


def check_pending_notification(user, message):
    missed_notifies = DiceEvent.objects.filter(user=user, is_win=True, is_notified=False)
    count = len(missed_notifies)
    if not count:
        return
    markup = get_localized_choice(user, ru_text=HOME_MARKUP_RU, en_text=HOME_MARKUP_ENG)
    missed_notifies.update(is_notified=True)
    send_message(message, 'Вы не заходили в бота, разблокировали его или мы забыли прислать вам уведомление.\n'
                          f'За это время вы выиграли {count} раз', markup)


def wilson_score(up, down, z=1.64485):
    """
    https://habr.com/ru/company/darudar/blog/143188/
    отрицательное значение при up=0
    """
    if not up:
        return - min(100, down) / 100
    if not up and not down:
        return 0

    total = up + down
    up_rate = up / total
    return (
        up_rate + z ** 2 / (2 * total) -
        z * ((up_rate * (1 - up_rate) + z ** 2 / (4 * total)) / total) ** 0.5) / (1 + z ** 2 / total)


# проверка на blacklist или выигрыш в данном чате сегодня + расчет формулы
def calc_dice_reward(user, dice, chat_id):
    details = {}
    is_blacklisted = Exceptions.objects.filter(user=user).exists()
    details['blacklisted'] = is_blacklisted
    if is_blacklisted:
        return 0, details

    details['today'] = today = date.today()
    details['members'] = members = bot.get_chat_members_count(chat_id)

    user_stat = DiceEvent.objects \
        .values('chat_id') \
        .filter(user=user, date__date=today, is_win=True) \
        .annotate(chat_sum_user=Sum('summa'))

    user_won_day = 0
    is_chat_win = False
    for aggregation in user_stat:
        user_won_day += float(aggregation['chat_sum_user'])
        if aggregation['chat_id'] == chat_id:
            is_chat_win = True
    details['user_won_day'] = user_won_day
    details['is_chat_win'] = is_chat_win
    if is_chat_win:
        return 0, details

    chat_stat = DiceEvent.objects \
        .values('chat_id') \
        .filter(date__date=today, is_win=True) \
        .annotate(chat_sum=Sum('summa'))
    chat_stat = {d['chat_id']: d['chat_sum'] for d in chat_stat}

    details['chat_won_day'] = chat_won_day = float(chat_stat.get(chat_id, 0))
    details['total_won_day'] = total_won_day = float(sum(chat_stat.values()))

    user_settings = Tools.objects.get(pk=1)
    details['user_limit_day'] = user_limit_day = float(user_settings.user_limit_day)
    details['chat_limit_day'] = chat_limit_day = float(user_settings.chat_limit_day)
    details['total_limit_day'] = total_limit_day = float(user_settings.total_limit_day)

    chat_size_multiplier = members / 10000
    details['chat_size_multiplier'] = 1 if chat_size_multiplier > 1 else chat_size_multiplier
    details['user_limit_multiplier'] = user_limit_multiplier = 1 - user_won_day / user_limit_day
    details['chat_limit_multiplier'] = chat_limit_multiplier = 1 - chat_won_day / chat_limit_day
    details['total_limit_multiplier'] = total_limit_multiplier = 1 - total_won_day / total_limit_day

    dice_multiplier = dice - 1
    if dice_multiplier < 0:
        dice_multiplier = 0
    if dice_multiplier > 5:
        dice_multiplier = 5
    details['dice'] = dice
    details['dice_multiplier'] = dice_multiplier

    user_reputation = wilson_score(user.upvotes, user.downvotes)
    details['user_upvotes'] = user.upvotes
    details['user_downvotes'] = user.downvotes
    details['user_influence'] = None
    details['user_lifetime'] = None
    details['user_reputation'] = user_reputation

    reward = dice_multiplier * chat_size_multiplier * \
        user_limit_multiplier * chat_limit_multiplier * \
        total_limit_multiplier * (user_reputation + 1)
    reward = round(reward, 6)

    if reward + user_won_day > user_limit_day:
        reward = user_limit_day - user_won_day
    return reward, details


def on_dice_event(message):
    coin = Tools.objects.get(pk=1).coin
    user, _ = get_user_model(message.from_user)
    logger.info(f'Dice event start. {user} in chat#{message.chat.id} "{message.chat.title}"')

    dice_msg = bot.send_dice(
        message.chat.id,
        disable_notification=True,
        reply_to_message_id=message.message_id)
    logger.info(f'Dice: {dice_msg.dice_value}')

    reward, details = calc_dice_reward(user, dice_msg.dice_value, message.chat.id)
    logger.info(f'\nReward: {reward}\nDetails:\n{pformat(details)}\n')

    is_win = bool(reward)
    event = DiceEvent.objects.create(
        user=user,
        chat_id=message.chat.id,
        title_chat=message.chat.title,
        link_chat=message.chat.username,
        summa=reward,
        is_win=is_win)
    if not is_win:
        return

    logger.info('Schedule payment + notify')
    set_unbond_obj(event)
    notify_win(user, event, coin=coin)

    url = f'https://telegram.me/{bot.user.username}'
    take_money_markup = types.InlineKeyboardMarkup(row_width=1)
    take_money_btn_text = get_localized_choice(user, pk=5)
    take_money_markup.add(types.InlineKeyboardButton(take_money_btn_text, url=url))

    take_money_text = get_localized_choice(user, pk=7)
    reply_to(dice_msg, take_money_text.format(X=reward, coin_ticker=coin), take_money_markup)
    logger.info('Dice event ok.')


# -----------


@bot.message_handler(commands=['start'], func=is_private_text)
def command_start(message):
    user, is_created = get_user_model(message.from_user)
    check_pending_notification(user, message)
    if is_created:
        markup = get_localized_choice(user, ru_text=HOME_MARKUP_RU, en_text=HOME_MARKUP_ENG)
        text = get_localized_choice(user, 1)
        document = Text.objects.get(pk=1).attachment
        bot.send_document(message.chat.id, document, caption=text, reply_markup=markup)


@bot.message_handler(func=is_chat_admin_button)
def chat_admin(message):
    user, _ = get_user_model(message.from_user)
    chats = AllowedChat.objects.filter(creator=user, status='activated')
    if not chats:
        text = 'Вы должны быть создателем одного из чатов, в котором работает этот бот'
        button_text = 'Выберите чат'
        send_message(message, text, another_chat_markup(bot.user.username, button_text))
        return

    text = 'Чаты'
    send_message(message, text, chat_list_markup(chats))


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin.'))
def chat_detail(call):
    user, _ = get_user_model(call.from_user)
    chat_id = int(call.data.split('.')[-1])
    try:
        chat = AllowedChat.objects.get(chat_id=chat_id, creator=user, status='activated')
    except AllowedChat.DoesNotExist:
        return

    send_chat_detail(call.message, chat)


def send_chat_detail(root_message, chat):
    chat.refresh_from_db()
    w = MinterWallet.create()
    chat_wallet, _ = ChatWallet.objects.get_or_create(
        chat=chat, defaults={
            'address': w['address'],
            'mnemonic': w['mnemonic']
        })
    text = f'''
Адрес кошелька чата: `{chat_wallet.address}`
Seed: `{chat_wallet.mnemonic}`
Баланс: {chat_wallet.balance}'''
    markup = chat_actions_markup(chat)
    bot.edit_message_text(
        text, root_message.chat.id, root_message.message_id,
        reply_markup=markup, parse_mode='markdown')


def chat_setting_prompt(user, setting):
    headr = {
        'ulimit': '*User Reward Limit*',
        'climit': '*Chat Reward Limit*',
        'dt': '*Dice Time*'
    }
    descr = {
        'ulimit': 'Max. *single user* reward\n'
                  'Example input: `77.01 DICE`',
        'climit': 'Max. *chat total* reward 24h\n'
                  'Example input: `148.8 TIME`',
        'dt': 'Dice will be available in this time\n'
              'Example input: `17:00-18:00`'
    }
    return f'{headr[setting]}\n\n' \
           f'{descr[setting]}\n\n' \
        '__Send me the new value to update this setting__'


@bot.callback_query_handler(func=lambda call: call.data.startswith('set.'))
def chat_setting(call):
    user, _ = get_user_model(call.from_user)
    setting, chat_id = call.data.split('.')[1:]
    try:
        chat = AllowedChat.objects.get(chat_id=chat_id, creator=user, status='activated')
    except AllowedChat.DoesNotExist:
        return

    prompt_txt = chat_setting_prompt(user, setting)
    markup = cancel_markup()
    cid, mid = call.message.chat.id, call.message.message_id
    bot.edit_message_text(prompt_txt, cid, mid, reply_markup=markup, parse_mode='markdown')

    def _set_chat_param(update):
        if isinstance(update, CallbackQuery) and update.data == 'back':
            send_chat_detail(call.message, chat)
            return
        bot.delete_message(update.chat.id, update.message_id)
        try:
            if setting == 'dt':
                f, t = update.text.split('-')
                if f > t:
                    raise ValueError(f'From > To: ({f} - {t})')
                chat.dice_time_from = f
                chat.dice_time_to = t
                chat.save()
            else:
                text_parts = update.text.split()
                limit = text_parts[0]
                coin = 'TIME' if len(text_parts) == 1 else text_parts[1]
                if setting == 'ulimit':
                    chat.user_limit_day = Decimal(limit)
                    chat.coin = coin
                    chat.save()
                if setting == 'climit':
                    chat.chat_limit_day = Decimal(limit)
                    chat.coin = coin
                    chat.save()
        except Exception as exc:
            logger.debug(f'### {type(exc)}: {exc}')

        send_chat_detail(call.message, chat)

    bot.register_next_step_handler(call.message, _set_chat_param)


@bot.message_handler(func=lambda message: message.text == RULES_BTN_RU or message.text == RULES_BTN_EN)
def rules(message):
    user = User.objects.get(pk=message.chat.id)
    text = get_localized_choice(user, pk=4)
    markup = get_localized_choice(user, ru_text=HOME_MARKUP_RU, en_text=HOME_MARKUP_ENG)
    send_message(
        message,
        text.format(
            user_name=user.first_name,
            coin_ticker=Tools.objects.get(pk=1).coin),
        markup)


@bot.message_handler(func=lambda message: message.text == WALLET_BTN_RU or message.text == WALLET_BTN_EN)
def my_wallet(message):
    user = User.objects.get(pk=message.chat.id)
    wallet = MinterWallets.objects.get(user=user)
    wallet_obj = MinterWallet.create(mnemonic=wallet.mnemonic)
    private_key = wallet_obj['private_key']

    coin = Tools.objects.get(pk=1).coin
    # balances, nonce = wallet_balance(wallet_obj['address'], with_nonce=True)
    # logger.info(balances)
    # amount = balances.get(coin, Decimal(0)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN)
    amount = wallet.balance
    nonce = API.get_nonce(wallet.address)

    check_obj = MinterCheck(
        nonce=1, due_block=999999999, coin=coin, value=amount, gas_coin=coin, passphrase=wallet.mnemonic)
    check_str = check_obj.sign(private_key)
    redeem_tx = MinterRedeemCheckTx(check_str, check_obj.proof(wallet.address, ''), nonce=1, gas_coin=coin)
    redeem_tx.sign(private_key)
    redeem_tx_fee = API.estimate_tx_commission(redeem_tx.signed_tx, pip2bip=True)['result']['commission']
    logger.debug(f'Wallet balance: {amount}')
    logger.info(f'Redeem check tx fee: {redeem_tx_fee}')
    available_withdraw = amount - redeem_tx_fee

    send_tx = MinterSendCoinTx(coin, wallet.address, amount, nonce=nonce, gas_coin=coin)
    send_tx.sign(wallet_obj['private_key'])
    send_tx_fee = API.estimate_tx_commission(send_tx.signed_tx, pip2bip=True)['result']['commission']
    logger.info(f'Send tx fee: {send_tx_fee}')
    available_send = amount - send_tx_fee

    to_wallet_text = None
    timeloop_text = None
    redeem_url = None
    user_address = None
    if available_withdraw > 0:
        to_wallet_text = get_localized_choice(
            user, ru_text=f'На кошелек', en_text=f'To Wallet')
        passphrase = uuid()
        check_obj = MinterCheck(
            nonce=1, due_block=999999999, coin=coin, value=available_withdraw, gas_coin=coin,
            passphrase=passphrase)
        check_str = check_obj.sign(private_key)
        redeem_tx = MinterRedeemCheckTx(check_str, proof='', nonce=1, gas_coin=coin)
        redeem_url = MinterDeeplink(redeem_tx, data_only=True).generate(password=passphrase)

    if available_send > 0:
        user_address = get_user_timeloop_address(message.chat.id)
        timeloop_text = 'Time Loop'

    markup = wallet_markup(
        to_wallet_text=to_wallet_text,
        redeem_deeplink=redeem_url,
        timeloop_text=timeloop_text,
        user_address=user_address)
    text = get_localized_choice(user, pk=16)
    text = text.format(
        user_wallet_address=wallet.address,
        user_seed_phrase=wallet.mnemonic,
        amount=amount)
    send_message(message, text, markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('timeloop_'))
def timeloop(call):
    user = User.objects.get(pk=call.from_user.id)
    coin = Tools.objects.get(pk=1).coin
    wallet = MinterWallets.objects.get(user=user)
    wallet_obj = MinterWallet.create(mnemonic=wallet.mnemonic)
    # balances, nonce = wallet_balance(wallet_obj['address'], with_nonce=True)
    # amount = balances.get(coin, Decimal(0))
    amount = wallet.balance
    nonce = API.get_nonce(wallet.address)

    send_tx = MinterSendCoinTx(coin, wallet.address, amount, nonce=nonce, gas_coin=coin)
    send_tx.sign(wallet_obj['private_key'])
    tx_fee = API.estimate_tx_commission(send_tx.signed_tx, pip2bip=True)['result']['commission']
    available_send = amount - tx_fee

    if available_send <= 0:
        bot.answer_callback_query(call.id, text='Недостаточно средств')
        return

    user_timeloop_address = call.data.split('_')[-1]
    if not user_timeloop_address:
        bot.answer_callback_query(call.id, text='У вас нет аккаунта в игре.')
        return

    send(wallet_obj, user_timeloop_address, coin, available_send, gas_coin=coin)
    bot.answer_callback_query(call.id, text='Баланс успешно пополнен')


@bot.message_handler(func=is_group_text_reply)
def reply_handler(message):
    msg_normalized = ' '.join(filter(None, str(message.text).lower().split(' ')))
    original_msg = message.reply_to_message
    sender_user = message.from_user
    receiver_user = original_msg.from_user
    if sender_user.id == receiver_user.id:
        return
    user, _ = get_user_model(receiver_user)
    user.reply_count += 1
    user.save()

    if len(message.text) > 20:
        return

    downvote_triggers = Triggers.objects.filter(action='downvote')
    is_downvote = any(
        t.phrase == msg_normalized if t.exact else t.phrase.lower() in msg_normalized
        for t in downvote_triggers)
    if is_downvote:
        user.downvotes += 1
        user.save()
        return

    upvote_triggers = Triggers.objects.filter(action='upvote')
    is_upvote = any(
        t.phrase == msg_normalized if t.exact else t.phrase.lower() in msg_normalized
        for t in upvote_triggers)
    if is_upvote:
        user.upvotes += 1
        user.save()
        return


# Обработчик всех остальных сообщений (в группе отлавливаем триггеры)
@bot.message_handler(func=is_group_text)
def handle_messages(message):
    msg_normalized = ' '.join(filter(None, str(message.text).lower().split(' ')))

    for trigger in Triggers.objects.filter(action='dice'):
        if trigger.phrase.lower() not in msg_normalized:
            continue
        chat_obj, is_created = AllowedChat.objects.get_or_create(
            chat_id=message.chat.id,
            defaults={
                'link_chat': message.chat.username,
                'title_chat': message.chat.title
            })

        if not chat_obj.creator:
            creator = get_chat_creator(message.chat.id)
            chat_obj.creator = creator
            chat_obj.save()

        if chat_obj.status == 'restricted':
            return

        if chat_obj.status in [None, 'errored']:
            first_msg_ts = None
            try:
                first_msg_ts = get_chat_creation_date(message.chat.id)
                chat_obj.created_at = datetime.utcfromtimestamp(first_msg_ts)
            except Exception as exc:
                logger.error(
                    f'\nGet chat creation date error.\n'
                    f'id={message.chat.id} type={message.chat.type} title={message.chat.title}\n'
                    f'{type(exc)}: {exc}')
            if not first_msg_ts:
                chat_obj.status_updated_at = datetime.utcnow()
                chat_obj.status = 'errored'
                chat_obj.save()
                return
            release_datetime = datetime.strptime(RELEASE_UTC_DATETIME, '%Y-%m-%d %H:%M')
            if first_msg_ts > release_datetime.timestamp():
                chat_obj.status_updated_at = datetime.utcnow()
                chat_obj.status = 'restricted'
                chat_obj.save()
                return
            chat_obj.status_updated_at = datetime.utcnow()
            chat_obj.status = 'activated'
            chat_obj.save()

        now = datetime.utcnow()
        timenow = now.time()
        if timenow < chat_obj.dice_time_from or timenow > chat_obj.dice_time_to:
            return

        # проверяем  положен ли выигрыш
        today = now.date()
        user, is_created = get_user_model(message.from_user)

        user_won_this_chat_today = False if is_created else \
            DiceEvent.objects.filter(
                user=user, chat_id=message.chat.id,
                is_win=True, date__date=today
            ).exists()

        user.today_state.setdefault('date', str(today))
        if user.today_state['date'] != str(today):
            user.today_state['date'] = str(today)
            user.today_state.pop('warned_chats', None)
            user.today_state.pop('warned_today', None)

        user.today_state.setdefault('warned_chats', {})
        warned_here = user.today_state['warned_chats'].setdefault(str(message.chat.id), 0)
        if user_won_this_chat_today and warned_here < 1:
            button_text = 'Попробовать в другом чате'
            reply_to(
                message, 'В этом чате вы уже не можете сегодня играть.'
                         '\nНе нужно спамить чат, мой уважаемый друг',
                another_chat_markup(bot.user.username, button_text))
            user.today_state['warned_chats'][str(message.chat.id)] += 1
            user.save()
            return
        if user_won_this_chat_today and warned_here >= 1:
            user.save()
            return

        user_stat = DiceEvent.objects \
            .values('user') \
            .filter(user=user, date__date=today, is_win=True) \
            .annotate(sum_user=Sum('summa'))

        total_user_reward = float(user_stat[0]['sum_user']) if user_stat else 0
        settings = Tools.objects.get(pk=1)
        warned_today = user.today_state.setdefault('warned_today', 0)
        if total_user_reward >= settings.user_limit_day and warned_today < 1:
            reply_to(message, 'Сегодня вы не можете больше играть.'
                              '\nНе нужно спамить чат, мой уважаемый друг', None)
            user.today_state['warned_today'] += 1
            user.save()
            return
        if total_user_reward >= settings.user_limit_day and warned_today >= 1:
            user.save()
            return
        user.save()
        on_dice_event(message)
        return


# -----
def is_bot_creator_in_group(m):
    return \
        m.chat.type in ('group', 'supergroup') and \
        m.from_user.id in settings.ADMIN_TG_IDS


def is_private(m):
    return m.chat.type == 'private'


@bot.message_handler(commands=['dice'], func=lambda m: is_bot_creator_in_group(m) or is_private(m))
def dice_test(message):
    user, _ = get_user_model(message.from_user or message.reply_to_message.from_user)

    args = message.text.split(' ')[1:]
    dice, chat_id = None, message.chat.id
    if len(args) == 1 and args[0].isdigit():
        dice = int(args[0])
    if not dice:
        dice = randint(1, 6)

    reward, details = calc_dice_reward(user, dice, chat_id)
    response = f"""
Dice testdata for [{user.username or user.first_name}](tg://user?id={user.pk})
```
Dice: {dice!s}
Reward: {reward!s}
Details:
{pformat(details, indent=2)}
```
"""
    markup = get_localized_choice(user, ru_text=HOME_MARKUP_RU, en_text=HOME_MARKUP_ENG)
    send_message(message, response, markup if message.chat.type == 'private' else KB_REMOVE)
