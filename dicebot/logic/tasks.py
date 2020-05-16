import logging

from pyrogram import Client
from pyrogram.errors import RPCError, UserIsBlocked, PeerIdInvalid, UserIsBot

from celery_app import app
from dice_time.settings import API_TOKEN, TG_API_HASH, TG_API_ID
from dicebot.logic.minter import coin_send, find_gas_coin, coin_multisend
from dicebot.logic.telegram import client
from users.models import User

logger = logging.getLogger('Dice')


@app.task
def minter_send_coins(
        w_from, addresses_to, coin, amount,
        group_chat_id, tg_id_sender, tg_id_receiver):
    if not addresses_to:
        return

    u_sender = User.objects.get(id=tg_id_sender)
    u_receivers_dict = {u.id: u for u in User.objects.filter(id__in=tg_id_receiver)}
    u_receivers = list(u_receivers_dict.values())
    gas_coin = find_gas_coin(w_from['address'])

    multi = len(addresses_to) > 1
    amount_single = amount / len(u_receivers) if multi else amount
    if not multi:
        logger.info(f'--- P2P Send Coin ({u_sender} -> {u_receivers[0]})  ---')
        r = coin_send(w_from['private_key'], w_from['address'], addresses_to[0], coin, amount, gas_coin=gas_coin)
        logger.info(f'--- P2P Send Result: {r} ---')
    else:
        logger.info(f'--- P2P Multisend Coin ({u_sender} -> {"|".join(str(u) for u in u_receivers)}  ---')
        multisend_list = [{'coin': coin, 'to': address, 'value': amount_single} for address in addresses_to]
        r = coin_multisend(w_from['private_key'], w_from['address'], multisend_list, gas_coin=gas_coin)
        logger.info(f'--- P2P Send Result: {r} ---')
    with client('session_sendcoins') as bot:
        u_receiver = None if multi else u_receivers[0]
        if 'error' not in r:
            markdown_receiver = f'{len(u_receivers)} users' if multi else u_receiver.profile_markdown
            text_sender = u_sender.choice_localized(text_name='msg-p2p-send').format(
                receiver=markdown_receiver, amount=amount, coin=coin)


            try:
                bot.send_message(tg_id_sender, text_sender)
            except UserIsBlocked:
                pass

            for tg_id_recv, u_recv in u_receivers_dict.items():
                try:
                    text_receiver = u_recv.choice_localized(text_name='msg-p2p-recv').format(
                        sender=u_sender.profile_markdown, amount=amount_single, coin=coin)
                    bot.send_message(tg_id_recv, text_receiver)
                except (UserIsBot, UserIsBlocked, PeerIdInvalid):
                    text_chat = u_recv.choice_localized(text_name='msg-p2p-recv-chat').format(
                        sender=u_sender.profile_markdown, receiver=u_recv.profile_markdown,
                        amount=amount_single, coin=coin)
                    bot.send_message(group_chat_id, text_chat)

        if 'error' in r and r['error'].get('tx_result', {}).get('code') == 107:
            no_coins_text = u_sender.choice_localized(text_name='msg-p2p-send-insuficcient').format(coin=coin)
            bot.send_message(tg_id_sender, no_coins_text)
