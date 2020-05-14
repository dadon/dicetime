import logging
from datetime import datetime, timedelta
from time import time
from typing import Union, Type

from mintersdk.sdk.wallet import MinterWallet
from pyrogram import Client

from dicebot.logic.minter import API, coin_send, coin_multisend, find_gas_coin
from dicebot.logic.helpers import truncate
from users.models import ChatWallet, MinterWallets, Payment, Tools

logger = logging.getLogger('DiceJobs')

BALANCE_API_BATCH_SIZE = 155
BALANCE_JOB_UPD_BATCH_SIZE = 500

USER_BALANCE_JOB_INTERVAL = 10
CHAT_BALANCE_JOB_INTERVAL = 10

PAYMENT_JOB_INTERVAL = 300
PAYMENT_JOB_MAX_MULTISEND = 75

LOCAL_PAYMENT_JOB_INTERVAL = 120


def update_balances(app: Client, model: Union[Type[ChatWallet], Type[MinterWallets]], notify: bool = True):
    now = datetime.utcnow()
    to_update = model.objects \
        .filter(balance_updated_at__lte=now - timedelta(seconds=5)) \
        .order_by('balance_updated_at')
    balances = {wallet.address: wallet.balance for wallet in to_update}

    balances_to_update = {}
    balances_diff = {}
    addresses = list(balances.keys())
    batches = [
        addresses[i: i + BALANCE_API_BATCH_SIZE]
        for i in range(0, len(addresses), BALANCE_API_BATCH_SIZE)
    ]

    start_time = time()
    for batch in batches:
        response = API.get_addresses(batch, pip2bip=True)['result']
        now_ = datetime.utcnow()
        for bal in response:
            new_balance = bal['balance']
            update_data = {
                'balance_updated_at': now_,
                'balances': {
                    _coin: str(_balance) for _coin, _balance in new_balance.items()
                }
            }
            balances_to_update[bal['address']] = update_data
            for coin, new_bal in new_balance.items():
                cur_bal = balances[bal['address']][coin]
                balances_diff.setdefault(bal['address'], {})
                if new_bal != cur_bal:
                    balances_diff[bal['address']][coin] = new_bal - cur_bal

    logger.info(f'Get balances from API ({len(addresses)} addrs, {len(batches)} batches) {time() - start_time} sec.')

    start_time = time()
    to_update.pg_bulk_update(balances_to_update, key_fields='address', batch_size=BALANCE_JOB_UPD_BATCH_SIZE)

    logger.info(f'DB update in {time() - start_time} sec.')

    if not notify or model == MinterWallets or not balances_diff:
        return

    # notify chat wallets
    chat_wallet_updated = [
        chat_wallet for chat_wallet in to_update
        if chat_wallet.address in balances_diff
    ]
    for chat_wallet in chat_wallet_updated:
        diff = balances_diff[chat_wallet.address]

        for coin, coindiff in diff.items():
            if coindiff <= 0:
                continue
            txt = chat_wallet.chat.creator.choice_localized(text_name='msg-chat-wallet-balance-update').format(
                title=chat_wallet.chat.title_chat, X=truncate(coindiff, 4), coin=coin)
            app.send_message(chat_wallet.chat.creator.id, txt)
            app.send_message(chat_wallet.chat.chat_id, txt)


def make_multisend_list_and_pay():
    multisend_list = []
    gifts = Payment.objects.filter(is_payed=False, wallet_local=None)[:PAYMENT_JOB_MAX_MULTISEND]

    if not gifts:
        logger.info(f'No events to pay')
        return

    settings = Tools.objects.get(pk=1)
    wallet_from = MinterWallet.create(mnemonic=settings.mnemonic)

    if len(gifts) == 1:
        g = gifts[0]
        response = coin_send(
            wallet_from['private_key'], wallet_from['address'],
            g.to, g.coin, g.amount, gas_coin=g.coin, payload=settings.payload)
        if 'error' not in response:
            g.is_payed = True
            g.save()
        return

    for g in gifts:
        multisend_list.append({'coin': g.coin, 'to': g.to, 'value': g.amount})
        g.is_payed = True

    response = coin_multisend(
        wallet_from['private_key'], wallet_from['address'], multisend_list,
        gas_coin=settings.coin, payload=settings.payload)

    if 'error' not in response:
        Payment.objects.bulk_update(gifts, ['is_payed'])


def local_chat_pay():
    settings = Tools.objects.get(pk=1)
    gift = Payment.objects.filter(is_payed=False, wallet_local__isnull=False).first()
    if not gift:
        return
    logging.info(f'Local gift payment ({gift.wallet_local.chat.title_chat}):')
    wallet = MinterWallet.create(mnemonic=gift.wallet_local.mnemonic)
    gas_coin = find_gas_coin(wallet['address'])

    response = coin_send(
        wallet['private_key'], wallet['address'], gift.to, gift.coin, gift.amount,
        gas_coin=gas_coin, payload=settings.payload + ' (chat owner bonus)')
    if 'error' not in response:
        gift.is_payed = True
        gift.save()
