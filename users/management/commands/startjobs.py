import logging
from datetime import datetime, timedelta
from decimal import Decimal, getcontext, ROUND_DOWN
from time import time

from django.core.management.base import BaseCommand
from mintersdk.sdk.wallet import MinterWallet

from users.minter import send, multisend, API
from users.models import Payment, Tools, MinterWallets, ChatWallet
from apscheduler.schedulers.blocking import BlockingScheduler

from users.tools import log_setup

scheduler = BlockingScheduler()
# log_setup(logging.DEBUG)
logger = logging.getLogger('Dice')

BALANCE_API_BATCH_SIZE = 155
BALANCE_JOB_GET_BATCH_SIZE = 2500
BALANCE_JOB_UPD_BATCH_SIZE = 500

USER_BALANCE_JOB_INTERVAL = 20
CHAT_BALANCE_JOB_INTERVAL = 4.7
PAYMENT_JOB_INTERVAL = 60


def __update_balances(model):
    logger.info('--------------------------')
    logger.info(f'Balance update job started ({model})')
    now = datetime.utcnow()
    coin = Tools.objects.get(pk=1).coin
    to_update = model.objects \
        .filter(balance_updated_at__lte=now - timedelta(seconds=5)) \
        .order_by('balance_updated_at')[:BALANCE_JOB_GET_BATCH_SIZE]
    balances = {wallet.address: wallet.balance for wallet in to_update}

    logger.info(f'{len(balances)} addresses to check')
    balances_to_update = {}
    addresses = list(balances.keys())
    batches = [
        addresses[i: i + BALANCE_API_BATCH_SIZE]
        for i in range(0, len(addresses), BALANCE_API_BATCH_SIZE)
    ]
    total_time = 0
    for batch in batches:
        t = time()
        response = API.get_addresses(batch, pip2bip=True)['result']
        balances_to_update.update({
            bal['address']: bal['balance'].get(coin, Decimal(0)).quantize(Decimal('0.123456'), rounding=ROUND_DOWN)
            for bal in response
            if bal['balance'].get(coin, Decimal(0)).quantize(Decimal('0.123456'), rounding=ROUND_DOWN) != balances[bal['address']]
        })
        iter_time = time() - t
        total_time += iter_time
        logger.info(f'Get addresses {len(batch)}: iter={iter_time}, total={total_time}')

    if not balances_to_update:
        logger.info(f'No balance changes')
        return

    logger.info(f'Updating {len(balances_to_update)} rows...')
    now = datetime.utcnow()
    t = time()
    to_update.pg_bulk_update({
        address: {
            'balance': balance,
            'balance_updated_at': now
        } for address, balance in balances_to_update.items()
    }, key_fields='address', batch_size=BALANCE_JOB_UPD_BATCH_SIZE)
    logger.info(f'Updated in {time() - t} seconds.')
    logger.info('--------------------------')


def make_multisend_list_and_pay():
    LIMIT=75
    multisend_list = []
    gifts = Payment.objects.filter(is_payed=False)[:LIMIT]

    if not gifts:
        logger.info(f'No events to pay')
        return

    settings = Tools.objects.get(pk=1)
    wallet_from = MinterWallet.create(mnemonic=settings.mnemonic)

    if len(gifts) == 1:
        g = gifts[0]
        response = send(wallet_from, g.to, g.coin, g.amount, gas_coin=g.coin, payload=settings.payload)
        if 'error' not in response:
            g.is_payed = True
            g.save()
        return

    for g in gifts:
        multisend_list.append({'coin': g.coin, 'to': g.to, 'value': g.amount})
        g.is_payed = True

    response = multisend(
        wallet_from=wallet_from,
        w_dict=multisend_list,
        gas_coin=settings.coin,
        payload=settings.payload)

    if 'error' not in response:
        Payment.objects.bulk_update(gifts, ['is_payed'])
        # gifts.pg_bulk_update([
        #     (g.id, g.balance) for g in gifts], fields='id', )


def update_user_balances():
    __update_balances(MinterWallets)


def update_chat_balances():
    __update_balances(ChatWallet)


class Command(BaseCommand):
    def handle(self, **options):
        scheduler.add_job(update_user_balances, 'interval', seconds=USER_BALANCE_JOB_INTERVAL)
        scheduler.add_job(update_chat_balances, 'interval', seconds=CHAT_BALANCE_JOB_INTERVAL)
        scheduler.add_job(make_multisend_list_and_pay, 'interval', seconds=PAYMENT_JOB_INTERVAL)
        scheduler.start()
