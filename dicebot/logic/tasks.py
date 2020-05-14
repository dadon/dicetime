import logging

from pyrogram import Client
from pyrogram.errors import RPCError

from celery_app import app
from dice_time.settings import API_TOKEN, TG_API_HASH, TG_API_ID
from dicebot.logic.minter import coin_send, find_gas_coin
from users.models import User

logger = logging.getLogger('Dice')


@app.task
def minter_send_coins(
        w_from, address_to, coin, amount,
        group_chat_id, tg_id_sender, tg_id_receiver, markdown_sender, markdown_receiver):

    u_sender = User.objects.get(id=tg_id_sender)
    u_receiver = User.objects.get(id=tg_id_receiver)

    logger.info(f'--- P2P Send Coin ({u_sender} -> {u_receiver})  ---')
    gas_coin = find_gas_coin(w_from['address'])
    r = coin_send(w_from['private_key'], w_from['address'], address_to, coin, amount, gas_coin=gas_coin)
    logger.info(f'--- P2P Send Result: {r} ---')

    with Client('pyrosession', no_updates=True, api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN) as client:

        if 'error' not in r:
            u_sender = User.objects.get(id=tg_id_sender)
            u_receiver = User.objects.get(id=tg_id_receiver)
            text_receiver = u_receiver.choice_localized(text_name='msg-p2p-recv').format(
                sender=markdown_sender, amount=amount, coin=coin)
            text_sender = u_sender.choice_localized(text_name='msg-p2p-send').format(
                receiver=markdown_receiver, amount=amount, coin=coin)
            try:
                client.send_message(tg_id_sender, text_sender)
                client.send_message(tg_id_receiver, text_receiver)
            except RPCError:
                text_chat = u_receiver.choice_localized(text_name='msg-p2p-recv-chat').format(
                    sender=markdown_sender, receiver=markdown_receiver, amount=amount, coin=coin)
                client.send_message(group_chat_id, text_chat)

        if 'error' in r and r['error'].get('tx_result', {}).get('code') == 107:
            no_coins_text = u_sender.choice_localized(text_name='msg-p2p-send-insuficcient').format(coin=coin)
            client.send_message(tg_id_sender, no_coins_text)
