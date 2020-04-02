import datetime
import telebot
from telebot import types

import mintersdk
from mintersdk.minterapi import MinterAPI
from mintersdk.sdk.wallet import MinterWallet
from mintersdk.sdk.transactions import MinterTx, MinterSendCoinTx, MinterBuyCoinTx


import requests
from .models import *
from dice_time.settings import API_TOKEN, ORIGIN
import re

import time

from .texts import *
from .markups import *

from django.conf import settings


bot = telebot.TeleBot(API_TOKEN)
botInfo = bot.get_me()

API = MinterAPI(settings.NODE_API_URL, **settings.TIMEOUTS)


def send(wallet_from, wallet_to, coin, value, gas_coin='BIP', payload=''):
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
    print(f'Send TX response:\n{r}')
    return send_tx


def send_cash(user, value):
    wallet_from = MinterWallet.objects.create(
        mnemonic=Tools.objects.get(pk=1).join)
    wallet_to = MinterWallets.objects.get(user=user).number
    coin = str(Tools.objects.get(pk=1).coin)
    payload = str(Tools.objects.get(pk=1).payload)
    send(
        wallet_from=wallet_from,
        wallet_to=wallet_to,
        coin=coin,
        value=value,
        gas_coin='BIP',
        payload=payload)


def send_message(message, text, markup):
    bot.send_message(
        message.chat.id,
        text=text,
        parse_mode='markdown',
        reply_markup=markup
    )


def edit_message_text(call, bot, text, markup):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='markdown',
        reply_markup=markup)


def edit_message_text2(call, bot, text):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode='markdown',
        text=text)

# регистрация юзера


def register(message):
    user = User.objects.create(
        id=message.from_user.id,
        is_bot=message.from_user.is_bot,
        last_name=message.from_user.last_name,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )
    #wallet = MinterWallet.create()
    # wal=MinterWallets.objects.create(user=user,number=wallet['address'],mnemonic=wallet['mnemonic'])

    return user


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def command_start(message):
    print("start")
    # Если пользователь уже зарегистрирован

    if User.objects.filter(pk=message.chat.id).exists():

        send_message(message, hello_text, HOME_MARKUP)

    # Иначе регистрируем пользователя
    else:

        user = register(message)
        # Включить, когда будет мультиязичность
        # send_message(message,choose_language_text,language_markup)

        send_message(message, hello_text, HOME_MARKUP)


# Обработка кнопки ⚠️ Правила
@bot.message_handler(func=lambda message: message.text == '⚠️ Правила')
def rooles(message):
    user = User.objects.get(pk=message.chat.id)
    send_message(
        message,
        rooles_text.format(
            user_name=user.first_name,
            coin_ticker=str(
                Tools.objects.get(
                    pk=1).coin)),
        None)

# Запуск игральной кости


def get_dice_event():

    # Запуск игральной кости
    # где number-это выпавшая кость
    #number = do()
    number = 3
    return number

# Расчет формулы и проверка на выигрыш в данном чате сегодня


def formula_calculation(number, chat_id):
    date = datetime.date.today()
    summa = 0
    answer_number = 1  # тут должна быть формула подсчета, которая вернет победное число
    if number == answer_number and not DiceEvent.objects.filter(
            chat_id=chat_id, date=date, is_win=True).exists():
        # сумма выиыгрыша
        summa = 1

    return summa


# Обработчик всех остальных сообщений ( в группе отлавливаем триггеры)
@bot.message_handler(func=lambda message: message.chat.type != 'private')
def handle_messages(message):

    text = str(message.text)
    print(text)
    print(message.chat.username)
    print(message.chat.title)
    for trigger in Triggers.objects.all():
        if text.find(trigger.name) > -1:
            bot.send_message(
                message.chat.id, text='Я стриггерил сообщение в ' + str((message.chat.title)))
            if User.objects.filter(pk=message.from_user.id).exists():
                user = User.objects.get(pk=message.from_user.id)
            else:
                user = register(message)
            # event = DiceEvent.objects.create(user = user, chat_id=int(message.chat.id),\
            # title_chat=message.chat.title, link_chat=message.chat.username)
            number = get_dice_event()
            #summa = formula_calculation(number,int(message.chat.id))
            # if summa > 0:
            #    event
            break
