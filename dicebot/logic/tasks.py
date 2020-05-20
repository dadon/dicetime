import logging
from typing import List

from pyrogram.errors import UserIsBlocked, PeerIdInvalid, UserIsBot

from celery_app import app
from dicebot.bot.markup import markup_take_money
from dicebot.logic.domain import get_user_model_many
from dicebot.logic.minter import coin_send, find_gas_coin, coin_multisend
from dicebot.logic.telegram import client, get_unique_prev_users
from users.models import User, ChatAirdrop, MinterWallets

logger = logging.getLogger('Dice')


@app.task
def chat_airdrop_last_n(airdrop_id):
    airdrop = ChatAirdrop.objects.get(id=airdrop_id)

    with client(':memory:') as bot:
        users = get_unique_prev_users(
            bot, airdrop.chat.chat_id, airdrop.message_id,
            limit=airdrop.users_total, exclude=[airdrop.sender.id])
        get_user_model_many(users)
        drop_to = MinterWallets.objects.filter(user__id__in=[u.id for u in users])
        minter_send_coins(
            airdrop.sender.wallet.minter_wallet, [w.address for w in drop_to],
            airdrop.coin, airdrop.amount,
            airdrop.chat.chat_id, airdrop.sender.id, [u.id for u in users],
            force_chat_notify=True, bot=bot)


@app.task
def minter_send_coins(
        w_from, addresses_to, coin, amount,
        group_chat_id, tg_id_sender, tg_id_receiver: List, force_chat_notify=False, bot=None):
    logger.info(f'--------minter_send_coins--------- {w_from, addresses_to, coin, amount, group_chat_id, tg_id_sender, tg_id_receiver, force_chat_notify}')
    if not addresses_to:
        return
    u_sender = User.objects.get(id=tg_id_sender)
    u_receivers_dict = {u.id: u for u in User.objects.filter(id__in=tg_id_receiver)}
    u_receivers = list(u_receivers_dict.values())
    gas_coin = find_gas_coin(w_from['address'])

    multi = len(addresses_to) > 1
    if not multi:
        logger.info(f'--- P2P Send Coin ({u_sender} -> {u_receivers[0]})  ---')
        r = coin_send(w_from['private_key'], w_from['address'], addresses_to[0], coin, amount, gas_coin=gas_coin)
        logger.info(f'--- P2P Send Result: {r} ---')
    else:
        logger.info(f'--- P2P Multisend Coin ({u_sender} -> {"|".join(str(u) for u in u_receivers)}  ---')
        multisend_list = [{'coin': coin, 'to': address, 'value': amount} for address in addresses_to]
        r = coin_multisend(w_from['private_key'], w_from['address'], multisend_list, gas_coin=gas_coin)
        logger.info(f'--- P2P Send Result: {r} ---')
    if not bot:
        bot = client('session_sendcoins')
        bot.start()
    try:
        u_receiver = None if multi else u_receivers[0]
        if 'error' not in r:
            markdown_receiver = f'{len(u_receivers)} users' if multi else u_receiver.profile_markdown
            text_sender = u_sender.choice_localized(text_name='msg-p2p-send').format(
                receiver=markdown_receiver, amount=amount, coin=coin)


            try:
                bot.send_message(tg_id_sender, text_sender)
            except UserIsBlocked:
                pass

            chat_notify = False
            for tg_id_recv, u_recv in u_receivers_dict.items():
                try:
                    text_receiver = u_recv.choice_localized(text_name='msg-p2p-recv').format(
                        sender=u_sender.profile_markdown, amount=amount, coin=coin)
                    bot.send_message(tg_id_recv, text_receiver)

                except (UserIsBot, UserIsBlocked, PeerIdInvalid):
                    chat_notify = True

            chat_notify = chat_notify or force_chat_notify
            if chat_notify:
                text_chat = u_sender.choice_localized(text_name='msg-p2p-recv-chat').format(
                    sender=u_sender.profile_markdown,
                    receiver=' '.join(u_recv.profile_markdown for u_recv in u_receivers),
                    amount=amount, coin=coin)
                bot_user = bot.get_me()
                take_money_btn_text = u_sender.choice_localized(text_name='btn-chat-win')
                bot.send_message(
                    group_chat_id, text_chat,
                    reply_markup=markup_take_money(bot_user.username, take_money_btn_text))

        if 'error' in r and r['error'].get('tx_result', {}).get('code') == 107:
            no_coins_text = u_sender.choice_localized(text_name='msg-p2p-send-insuficcient').format(coin=coin)
            bot.send_message(tg_id_sender, no_coins_text)
    except Exception:
        logger.exception('ERROR SEND COINS')
        bot.stop()
