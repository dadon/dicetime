import logging

from pyrogram import Client

from celery_app import app
from dice_time.settings import API_TOKEN, TG_API_HASH, TG_API_ID
from dicebot.logic.minter import coin_send, API, estimate_custom_send_fee, find_gas_coin

logger = logging.getLogger('Dice')


@app.task
def minter_send_coins(
        w_from, address_to, coin, amount,
        group_chat_id, tg_id_sender, tg_id_receiver, markdown_sender, markdown_receiver):
    logger.info('--- P2P Send Coin ---')

    gas_coin = find_gas_coin(w_from['address'])
    r = coin_send(w_from['private_key'], w_from['address'], address_to, coin, amount, gas_coin=gas_coin)
    client = Client('pyrosession', no_updates=True, api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN)
    client.start()

    logger.info(f'--- P2P Send Result: {r} ---')
    if 'error' not in r:
        text = f'{markdown_sender} отправил вам {amount} {coin}'
        text_sender = f'Вы отправили {markdown_receiver} {amount} {coin}'
        client.send_message(tg_id_sender, text_sender, parse_mode='markdown')
        msg = client.send_message(tg_id_receiver, text, parse_mode='markdown')
        if msg == 403:
            text = f'{markdown_sender} отправил {markdown_receiver} {amount} {coin}'
            client.send_message(group_chat_id, text, parse_mode='markdown')

    if 'error' in r and r['error'].get('tx_result', {}).get('code') == 107:
        no_coins_text = f'Недостаточно монет {coin} на вашем кошельке'
        client.send_message(tg_id_sender, no_coins_text)

    client.stop()
