import datetime
import telebot
from telebot import types

import mintersdk
from mintersdk.minterapi import MinterAPI
from mintersdk.sdk.wallet import MinterWallet
from mintersdk.sdk.transactions import MinterTx, MinterSendCoinTx, MinterBuyCoinTx


import requests

from .dice import DiceBot
from .models import *
from dice_time.settings import API_TOKEN, ORIGIN, LOCAL, BETA, PROD
import re

import time

from .markups import *

from django.conf import settings


bot = DiceBot(API_TOKEN, skip_pending=True)
botInfo = bot.get_me()
print('Me: ', botInfo)

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
    print(f'Sending: {value} {coin} -> {wallet_to}')
    if API_TOKEN in [BETA, PROD]:
        r = API.send_transaction(send_tx.signed_tx)
        print(f'Send TX response:\n{r}')
    return send_tx


def send_cash(event):
    event.is_payed=True
    event.save()
    wallet_from = MinterWallet.create(
        mnemonic=Tools.objects.get(pk=1).join)
    wallet_to = MinterWallets.objects.get(user=event.user).number
    coin = str(Tools.objects.get(pk=1).coin)
    payload = str(Tools.objects.get(pk=1).payload)

    send(
        wallet_from=wallet_from,
        wallet_to=wallet_to,
        coin=coin,
        value=event.summa,
        gas_coin=coin,
        payload=payload)
    


def send_message(message, text, markup):
    bot.send_message(
        message.chat.id,
        text=text,
        parse_mode='markdown',
        reply_markup=markup,
        disable_web_page_preview=True
    )

def return_text(user,pk):
    if user.language.pk==1:
        text=Texts.objects.get(pk=pk).text_ru
    else:
        text=Texts.objects.get(pk=pk).text_eng
    return text

def check_event(user, event_id, message):
    if DiceEvent.objects.filter(pk=event_id).exists():
        event = DiceEvent.objects.get(pk=event_id)
        ms=Tools.objects.get(pk=1).ms

        if user.language.pk == 1:
            markup = HOME_MARKUP_RU
        else:
            markup = HOME_MARKUP_ENG

        if event.user == user:
               
            wallet = MinterWallets.objects.get(user=user)
            text=return_text(user,15)
            send_message(message,text.format(user_name=user.first_name),None)
            time.sleep(ms)
            
            
            text=return_text(user,10)
            send_message(message,text.format(user_wallet_address=wallet.number),None)
            time.sleep(ms)

            text=return_text(user,11)
            send_message(message,text,None)
            time.sleep(ms)

            text=return_text(user,12)
            send_message(message,text.format(user_seed_phrase=wallet.mnemonic),None)
            time.sleep(ms)

            text=return_text(user,1)
            document=Texts.objects.get(pk=1).attachment
            bot.send_document(message.chat.id,document,caption=text)
            time.sleep(ms)

            text=return_text(user,14)
            send_message(message,text,markup)
            time.sleep(ms)

            if event.is_payed==False:
                send_cash(event)

        else:
            wallet = MinterWallets.objects.get(user=user)
            text=return_text(user,8)
            send_message(message,text,None)
            time.sleep(ms)

            text=return_text(user,9)
            send_message(message,text,None)
            time.sleep(ms)
           
            
            text=return_text(user,10)
            send_message(message,text.format(user_wallet_address=wallet.number),None)
            time.sleep(ms)

            text=return_text(user,11)
            send_message(message,text,None)
            time.sleep(ms)


            text=return_text(user,12)
            send_message(message,text.format(user_seed_phrase=wallet.mnemonic),None)
            time.sleep(ms)

            text=return_text(user,1)
            document=Texts.objects.get(pk=1).attachment
            bot.send_document(message.chat.id,document,caption=text)
            time.sleep(ms)

            text=return_text(user,14)
            send_message(message,text,markup)
            time.sleep(ms)


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
@bot.message_handler(commands=['start'])
def command_start(message):
    print("start")
    referal_id = int(message.text[12:] or -1)

    # Если пользователь уже зарегистрирован
    text=Texts.objects.get(pk=2).text_ru
    if User.objects.filter(pk=message.chat.id).exists():
        user = User.objects.get(pk=message.chat.id)
        if referal_id > -1:
            check_event(user, referal_id, message)
    # Иначе регистрируем пользователя
    else:

        user = register(message)
        send_message(message, text,language_markup)

    if not MinterWallets.objects.filter(user=user).exists():
        wallet = MinterWallet.create()
        wal=MinterWallets.objects.create(user=user,number=wallet['address'],mnemonic=wallet['mnemonic'])



@bot.callback_query_handler(func=lambda call: call.data.startswith('languag.id.'))
def choice_langeuage(call):
    user = User.objects.get(pk=call.message.chat.id)
    flag=int(call.data[11:])
    langeuage=Language.objects.get(pk=flag)
    user.language=langeuage
    user.save()
    if user.language.pk==1:
        text=Texts.objects.get(pk=1).text_ru
        markup = HOME_MARKUP_RU
    else:
        text=Texts.objects.get(pk=1).text_eng
        markup = HOME_MARKUP_ENG
    send_message(call.message, text, markup)
    document=Texts.objects.get(pk=1).attachment
    bot.send_document(call.message.chat.id,document)


# Обработка кнопки ⚠️ Правила
@bot.message_handler(func=lambda message: message.text == '⚠️ Правила' or message.text == '⚠️ Rules')
def rooles(message):
    user = User.objects.get(pk=message.chat.id)
    if user.language.pk==1:
        text=Texts.objects.get(pk=4).text_ru
    else:
        text=Texts.objects.get(pk=4).text_eng
    send_message(
        message,
        text.format(
            user_name=user.first_name,
            coin_ticker=str(
                Tools.objects.get(
                    pk=1).coin)),
        None)


# Обработка кнопки 💰 Мой Кошелёк
@bot.message_handler(func=lambda message: message.text == '💰 Мой Кошелёк' or message.text == '💰 My wallet')
def my_wallet(message):
    user = User.objects.get(pk=message.chat.id)
    wallet = MinterWallets.objects.get(user=user)
    amount = wallet_balance(wallet)
    if user.language.pk==1:
        text=Texts.objects.get(pk=16).text_ru
    else:
        text=Texts.objects.get(pk=16).text_eng
    send_message(
        message,
        text.format(
            user_wallet_address=wallet.number,
            user_seed_phrase=wallet.mnemonic, amount=amount), None)


# Расчет формулы и проверка на выигрыш в данном чате сегодня
def formula_calculation(user, number, chat_id):
    date = datetime.date.today()
    summa = 0
    if number > int(Tools.objects.get(pk=1).main_value) and not DiceEvent.objects.filter(
            chat_id=chat_id,
            date__date=date,
            is_win=True,user=user).exists() and not Exceptions.objects.filter(
            user=user).exists():

        # сумма выигрыша
        summa = number - 3  # формула подсчета выигрыша
    return summa


def reply_to(message, text, markup):
    mes = bot.reply_to(message=message, text=text, reply_markup=markup)
    return mes


def on_dice_event(message):
    # Письмо, к-ое отправляется ботом ( кидаем кубик )
    dice_msg = bot.send_dice(message.chat.id, disable_notification=True, reply_to_message_id=message.message_id)

    if User.objects.filter(pk=message.from_user.id).exists():
        user = User.objects.get(pk=message.from_user.id)
    else:
        user = register(message)
    event = DiceEvent.objects.create(
        user=user,
        chat_id=message.chat.id,
        title_chat=message.chat.title,
        link_chat=message.chat.username)

    summa = formula_calculation(user, dice_msg.dice_value, message.chat.id)
    if not summa:
        return

    url = 'https://telegram.me/' + str(botInfo.username) + '?start=event' + \
          str(event.id)
    take_money_markup = types.InlineKeyboardMarkup(row_width=1)
    if user.language.pk == 1:
        text_markup = Texts.objects.get(pk=5).text_ru
    else:
        text_markup = Texts.objects.get(pk=5).text_eng

    take_money_markup.add(
        types.InlineKeyboardButton(
            str(text_markup), url=url))

    event.summa = summa
    event.is_win = True
    event.save()

    if user.language.pk == 1:
        text = Texts.objects.get(pk=7).text_ru
    else:
        text = Texts.objects.get(pk=7).text_eng

    reply_to(dice_msg, text.format(X=summa, coin_ticker=str(
        Tools.objects.get(pk=1).coin)), take_money_markup)


# Обработчик всех остальных сообщений ( в группе отлавливаем триггеры)
@bot.message_handler(func=lambda message: message.chat.type != 'private')
def handle_messages(message):
    msg_normalized = ' '.join(filter(None, str(message.text).lower().split(' ')))

    for trigger in Triggers.objects.all():
        if trigger.name in msg_normalized:
            if message.chat.id not in [-1001363709875, -1001270954422]:
                print('somebody')
                print(message.chat)
                print(message.from_user)
                send_message(message, 'Тут нельзя)', None)
                return

            print('allowed', message.chat)
            on_dice_event(message)
            return
