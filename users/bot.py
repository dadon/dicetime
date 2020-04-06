import datetime
import logging
import os
from decimal import Decimal
from random import randint
from pprint import pformat
import telebot
from django.db.models import Count, Sum
from telebot import types

import mintersdk
from mintersdk.minterapi import MinterAPI
from mintersdk.sdk.wallet import MinterWallet
from mintersdk.sdk.transactions import MinterTx, MinterSendCoinTx, MinterBuyCoinTx, MinterMultiSendCoinTx

import requests
from telebot.types import Message

from dice_time.wsgi import scheduler
from .dice import DiceBot
from .models import *
from dice_time.settings import API_TOKEN,  ALLOWED_GROUPS, LOCAL
import re

import time

from .markups import *

from django.conf import settings


def is_group_text(msg):
    return msg.chat.type != 'private' and msg.text and not msg.text.startswith('/')


def is_private_text(msg):
    return msg.chat.type == 'private' and msg.text


logger = logging.getLogger('Dice')

bot = DiceBot(API_TOKEN, skip_pending=True, threaded=not LOCAL)
botInfo = bot.get_me()
logger.info(f'Me: {botInfo}')


API = MinterAPI(settings.NODE_API_URL, **settings.TIMEOUTS)


def multisend(wallet_from, w_dict, gas_coin='BIP', payload=''):
    for send_rec in w_dict:
        logger.info(f"Sending: {send_rec['value']} {send_rec['coin']} -> {send_rec['to']}")
    if LOCAL:
        return

    nonce = API.get_nonce(wallet_from['address'])
    tx = MinterMultiSendCoinTx(w_dict, nonce=nonce, gas_coin=gas_coin, payload=payload)
    tx.sign(wallet_from['private_key'])
    r = API.send_transaction(tx.signed_tx)
    logger.info(f'Send TX response:\n{r}')
    return tx


def send(wallet_from, wallet_to, coin, value, gas_coin='BIP', payload=''):
    logger.info(f'Sending: {value} {coin} -> {wallet_to}')
    if LOCAL:
        return
    nonce = API.get_nonce(wallet_from['address'])
    send_tx = MinterSendCoinTx(
        coin,
        wallet_to,
        value,
        nonce=nonce,
        gas_coin=gas_coin,
        payload=payload)
    send_tx.sign(wallet_from['private_key'])
    r = API.send_transaction(send_tx.signed_tx)
    logger.info(f'Send TX response:\n{r}')
    return send_tx


@scheduler.scheduled_job('interval', minutes=1)
def make_multisend_list_and_pay():
    LIMIT=75
    multisend_list = []
    gifts = Payment.objects.filter(is_payed=False)[:LIMIT]

    if not gifts:
        logger.info(f'No events to pay')
        return

    settings = Tools.objects.get(pk=1)
    wallet_from = MinterWallet.create(mnemonic=settings.join)

    if len(gifts) == 1:
        g = gifts[0]
        send(wallet_from, g.to, g.coin, g.amount, gas_coin=g.coin, payload=settings.payload)
        g.is_payed = True
        g.save()
        return

    for g in gifts:
        multisend_list.append({'coin': g.coin, 'to': g.to, 'value': g.amount})
        g.is_payed = True
        g.save()

    multisend(wallet_from=wallet_from, w_dict=multisend_list, gas_coin=settings.coin, payload=settings.payload)
            

def set_unbond_obj(event):
    if not event.summa:
        return
    event.is_payed=True
    event.save()
    wallet_to = MinterWallets.objects.get(user=event.user).number
    coin = str(Tools.objects.get(pk=1).coin)
    Payment.objects.create(
        user=event.user,
        event=event,
        to=wallet_to,
        coin=coin,
        amount=event.summa)
    

def send_message(chat_id, text, markup):
    chat_id = chat_id if isinstance(chat_id, int) else chat_id.chat.id
    bot.send_message(
        chat_id,
        text=text,
        parse_mode='markdown',
        reply_markup=markup,
        disable_web_page_preview=True
    )


def get_localized_choice(user, pk=None, ru_text='', en_text=''):
    if user.language.pk == 1:
        text = Texts.objects.get(pk=pk).text_ru if pk else ru_text
    else:
        text = Texts.objects.get(pk=pk).text_eng if pk else en_text
    return text


def notify_win(user, event, coin):
    chat_id = user.id
    send_message(chat_id, f'Начислено + {event.summa} {coin}', None)
    event.is_notified = True
    event.save()
    # ms = Tools.objects.get(pk=1).ms
    # markup = get_localized_choice(user, ru_text=HOME_MARKUP_RU, en_text=HOME_MARKUP_ENG)
    # wallet = MinterWallets.objects.get(user=user)
    # text = get_localized_choice(user, 15)
    # send_message(chat_id, text.format(user_name=user.first_name), None)
    # time.sleep(ms)
    # text = get_localized_choice(user, 10)
    # send_message(message, text.format(user_wallet_address=wallet.number), None)

    # text = get_localized_choice(user, 11)
    # send_message(chat_id, text, None)
    # time.sleep(ms)
    # text = get_localized_choice(user, 12)
    # send_message(message, text.format(user_seed_phrase=wallet.mnemonic), None)

    # text = get_localized_choice(user, 1)
    # document = Texts.objects.get(pk=1).attachment
    # bot.send_document(chat_id, document, caption=text)
    # time.sleep(ms)

    # text = get_localized_choice(user, 14)
    # send_message(chat_id, text, markup)
    # time.sleep(ms)


def check_pending_notification(user, message):
    missed_notifies = DiceEvent.objects.filter(user=user, is_win=True, is_notified=False)
    count = len(missed_notifies)
    if not count:
        return
    markup = get_localized_choice(user, ru_text=HOME_MARKUP_RU, en_text=HOME_MARKUP_ENG)
    for event in missed_notifies:
        event.is_notified = True
    missed_notifies.update(is_notified=True)
    send_message(message, 'Вы не заходили в бота, разблокировали его или мы забыли прислать вам уведомление. '
                          'Текста на этот случай нет, но за это время вы выиграли {missed} раз'.format(missed=count), markup)
            

def wallet_balance(wallet):
    URL_wallet = f'https://explorer-api.minter.network/api/v1/addresses/' + \
        str(wallet.number)
    r_wallet = requests.get(URL_wallet)
    balances = r_wallet.json()['data']['balances']
    amount = 0
    for b in balances:
        if str(b['coin']) == 'TIME':
            amount = float(b['amount'])
    return amount


# регистрация юзера
def register(message):
    user = User.objects.create(
        id=message.from_user.id,
        is_bot=message.from_user.is_bot,
        last_name=message.from_user.last_name,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )
    if not MinterWallets.objects.filter(user=user).exists():
        wallet = MinterWallet.create()
        wal=MinterWallets.objects.create(user=user,number=wallet['address'],mnemonic=wallet['mnemonic'])

    return user


# Обработчик команды /start
@bot.message_handler(commands=['start'], func=is_private_text)
def command_start(message):
    # Если пользователь уже зарегистрирован
    if User.objects.filter(pk=message.chat.id).exists():
        user = User.objects.get(pk=message.chat.id)
        check_pending_notification(user, message)

    # Иначе регистрируем пользователя
    else:
        user = register(message)
        text = get_localized_choice(user, pk=2)
        send_message(message, text, language_markup)

    if not MinterWallets.objects.filter(user=user).exists():
        logger.info('############## This should not be printed !!!!!!!!!!!!!!! NO wallet check')
        wallet = MinterWallet.create()
        MinterWallets.objects.create(user=user, number=wallet['address'], mnemonic=wallet['mnemonic'])


@bot.callback_query_handler(func=lambda call: call.data.startswith('languag.id.'))
def choice_langeuage(call):
    user = User.objects.get(pk=call.message.chat.id)
    flag=int(call.data[11:])
    langeuage=Language.objects.get(pk=flag)
    user.language=langeuage
    user.save()

    if flag == 1:
        text = Texts.objects.get(pk=1).text_ru
        markup = HOME_MARKUP_RU
    else:
        text = Texts.objects.get(pk=1).text_eng
        markup = HOME_MARKUP_ENG
    send_message(call.message, text, markup)

    text = get_localized_choice(user, 1)
    document = Texts.objects.get(pk=1).attachment
    bot.send_document(call.message.chat.id, document, caption=text)


# Обработка кнопки ⚠️ Правила
@bot.message_handler(func=lambda message: message.text == '⚠️ Правила' or message.text == '⚠️ Rules')
def rooles(message):
    user = User.objects.get(pk=message.chat.id)
    text = get_localized_choice(user, pk=4)
    send_message(
        message,
        text.format(
            user_name=user.first_name,
            coin_ticker=Tools.objects.get(pk=1).coin),
        None)


# проверка на blacklist или выигрыш в данном чате сегодня + расчет формулы
def formula_calculation(user, dice, chat_id):
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
    if is_chat_win and user.id not in settings.ADMINS:
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

    chat_size_multiplier = 1 + members / 10000
    details['chat_size_multiplier'] = 3 if chat_size_multiplier > 3 else chat_size_multiplier
    details['user_limit_multiplier'] = user_limit_multiplier = 1 - user_won_day / user_limit_day
    details['chat_limit_multiplier'] = chat_limit_multiplier = 1 - chat_won_day / chat_limit_day
    details['total_limit_multiplier'] = total_limit_multiplier = 1 - total_won_day / total_limit_day

    dice_number = dice - 3
    if dice_number < 0:
        dice_number = 0
    if dice_number > 3:
        dice_number = 3

    details['dice'] = dice
    details['dice_number'] = dice_number
    reward = round(
        dice_number * chat_size_multiplier * user_limit_multiplier * chat_limit_multiplier * total_limit_multiplier, 6)
    return reward, details


def reply_to(message, text, markup):
    mes = bot.reply_to(message=message, text=text, reply_markup=markup,parse_mode='markdown')
    return mes


def on_dice_event(message):
    # Письмо, к-ое отправляется ботом ( кидаем кубик )
    dice_msg = bot.send_dice(message.chat.id, disable_notification=True, reply_to_message_id=message.message_id)

    if User.objects.filter(pk=message.from_user.id).exists():
        user = User.objects.get(pk=message.from_user.id)
    else:
        user = register(message)

    reward, _ = formula_calculation(user, dice_msg.dice_value, message.chat.id)
    is_win = bool(reward)
    event = DiceEvent.objects.create(
        user=user,
        chat_id=message.chat.id,
        title_chat=message.chat.title,
        link_chat=message.chat.username,
        summa=reward,
        is_win=is_win)
    if reward:
        set_unbond_obj(event)
        time.sleep(1)
        notify_win(user, event, coin=Tools.objects.get(pk=1).coin)

        url = f'https://telegram.me/{botInfo.username}'
        take_money_markup = types.InlineKeyboardMarkup(row_width=1)
        text_markup = get_localized_choice(user, pk=5)
        take_money_markup.add(types.InlineKeyboardButton(text_markup, url=url))

        text = get_localized_choice(user, pk=7)
        reply_to(dice_msg, text.format(X=reward, coin_ticker=str(
            Tools.objects.get(pk=1).coin)), take_money_markup)
        logger.info('Dice event ok.')

# Обработчик всех остальных сообщений (в группе отлавливаем триггеры)
@bot.message_handler(func=is_group_text)
def handle_messages(message):
    msg_normalized = ' '.join(filter(None, str(message.text).lower().split(' ')))

    for trigger in Triggers.objects.all():
        if trigger.name in msg_normalized:
            if ALLOWED_GROUPS and message.chat.id not in ALLOWED_GROUPS:
                send_message(message, 'Тут нельзя)', None)
                return

            # проверяем  положен ли выигрыш
            today = date.today()
            user = User.objects.get(pk=message.from_user.id)

            user_won_this_chat_today = DiceEvent.objects.filter(
                user=user, chat_id=message.chat.id, is_win=True, date__date=today).exists()
            if user_won_this_chat_today:
                reply_to(message, 'В этом чате вы уже не можете сегодня играть.'
                                  '\nНе нужно спамить чат, мой уважаемый друг', None)
                return

            user_stat = DiceEvent.objects \
                .values('user') \
                .filter(user=user, date__date=today, is_win=True) \
                .annotate(sum_user=Sum('summa'))

            total_user_reward = float(user_stat[0]['sum_user']) if user_stat else 0
            settings = Tools.objects.get(pk=1)
            if total_user_reward >= settings.user_limit_day:
                reply_to(message, 'Сегодня вы не можете больше играть.'
                                  '\nНе нужно спамить чат, мой уважаемый друг', None)
                return

            on_dice_event(message)
            return


@bot.message_handler(commands=['update'], func=lambda m: m.from_user.id in settings.ADMINS)
def dice_test(message):
    os.system('git pull')


@bot.message_handler(commands=['dice'], func=lambda m: m.from_user.id in settings.ADMINS)
def dice_test(message):
    uid = message.from_user.id
    if message.reply_to_message:
        uid = message.reply_to_message.from_user.id

    if User.objects.filter(pk=uid).exists():
        user = User.objects.get(pk=uid)
    else:
        user = register(message.reply_to_message or message)

    args = message.text.split(' ')[1:]
    dice, chat_id = None, message.chat.id
    if len(args) == 1 and args[0].isdigit():
        dice = int(args[0])
    if not dice:
        dice = randint(1, 6)

    reward, details = formula_calculation(user, dice, chat_id)
    response = f"""
Dice testdata for [{user.username or user.first_name}](tg://user?id={user.pk})
```
Dice: {dice!s}
Reward: {reward!s}
Details:
{pformat(details)}
```
"""
    send_message(message, response, None)


# Обработка кнопки 💰 Мой Кошелёк
@bot.message_handler(func=lambda message: message.text == '💰 Мой Кошелёк' or message.text == '💰 My wallet')
def my_wallet(message):
    user = User.objects.get(pk=message.chat.id)
    wallet = MinterWallets.objects.get(user=user)
    amount = wallet_balance(wallet)
    text = get_localized_choice(user, pk=16)
    wallet_markup = get_localized_choice(user, ru_text=wallet_markup_ru, en_text=wallet_markup_eng)
    send_message(
        message,
        text.format(
            user_wallet_address=wallet.number,
            user_seed_phrase=wallet.mnemonic, amount=amount), wallet_markup)
