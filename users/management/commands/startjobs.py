import logging
from datetime import datetime, timedelta
from time import time

from django.core.management.base import BaseCommand
from mintersdk.sdk.wallet import MinterWallet

from users.bot import bot
from users.minter import send, multisend, API
from users.models import Payment, Tools, MinterWallets, ChatWallet
from users.misc import truncate
from apscheduler.schedulers.blocking import BlockingScheduler


scheduler = BlockingScheduler()
logger = logging.getLogger('DiceJobs')

BALANCE_API_BATCH_SIZE = 155
BALANCE_JOB_GET_BATCH_SIZE = 2500
BALANCE_JOB_UPD_BATCH_SIZE = 500

USER_BALANCE_JOB_INTERVAL = 4.7
CHAT_BALANCE_JOB_INTERVAL = 4.7
PAYMENT_JOB_INTERVAL = 300
LOCAL_PAYMENT_JOB_INTERVAL = 300


def __update_balances(model, notify=True):
    logger.info(f'-------------------------- Balance update job started ({model})')
    now = datetime.utcnow()
    to_update = model.objects \
        .filter(balance_updated_at__lte=now - timedelta(seconds=5)) \
        .order_by('balance_updated_at')[:BALANCE_JOB_GET_BATCH_SIZE]
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
            balances_to_update[bal['address']] = {'balance_updated_at': now_}
            balances_to_update[bal['address']]['balances'] = {c: str(b) for c, b in new_balance.items()}
            for coin, new_bal in new_balance.items():
                cur_bal = balances[bal['address']][coin]
                balances_diff.setdefault(bal['address'], {})
                if new_bal != cur_bal:
                    balances_diff[bal['address']][coin] = new_bal - cur_bal

    logger.info(f'Get balances from API ({len(addresses)} addrs, {len(batches)} batches) {time() - start_time} sec.')

    start_time = time()
    to_update.pg_bulk_update(balances_to_update, key_fields='address', batch_size=BALANCE_JOB_UPD_BATCH_SIZE)

    logger.info(f'DB update in {time() - start_time} sec.')
    logger.info('-------------------------- Balance update job finished ({model})')

    if not notify or model == MinterWallets or not balances_diff:
        return

    # notify chat wallets
    chat_wallet_updated = [
        chat_wallet for chat_wallet in to_update
        if chat_wallet.address in balances_diff
    ]

    logger.info(f'-------------------------- Send notifications ({len(chat_wallet_updated)} chat wallets)')
    for chat_wallet in chat_wallet_updated:
        diff = balances_diff[chat_wallet.address]

        for coin, coindiff in diff.items():
            if coindiff <= 0:
                continue
            txt = f'Баланс чата {chat_wallet.chat.title_chat} пополнен на {truncate(coindiff, 4)} {coin}'
            bot.send_message(chat_wallet.chat.creator.id, txt)
            bot.send_message(chat_wallet.chat.chat_id, txt)
    logger.info(f'-------------------------- Send notifications complete')


def make_multisend_list_and_pay():
    LIMIT=75
    multisend_list = []
    gifts = Payment.objects.filter(is_payed=False, wallet_local=None)[:LIMIT]

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


def local_chat_pay():
    logger.info('--------------------------')
    logger.info(f'Local payment job started')

    LIMIT = 10
    settings = Tools.objects.get(pk=1)
    gifts = Payment.objects.filter(is_payed=False, wallet_local__isnull=False)[:LIMIT]
    for gift in gifts:
        logging.info(f'Local gift payment ({gift.wallet_local.chat.title_chat}):')
        wallet = MinterWallet.create(mnemonic=gift.wallet_local.mnemonic)
        balance_bip = gift.wallet_local.balance['BIP']
        gas_coin = gift.coin
        if balance_bip >= 0.01:
            gas_coin = 'BIP'
        response = send(
            wallet, gift.to, gift.coin, gift.amount,
            gas_coin=gas_coin, payload=settings.payload + ' (chat owner bonus)')
        if 'error' not in response:
            gift.is_payed = True
            gift.save()


def update_user_balances():
    __update_balances(MinterWallets)


def update_chat_balances(notify):
    __update_balances(ChatWallet, notify=notify)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--notify', default='on')

    def handle(self, **options):
        logger.info(options)
        notify = options['notify'] == 'on'
        scheduler.add_job(update_user_balances, 'interval', seconds=USER_BALANCE_JOB_INTERVAL)
        scheduler.add_job(update_chat_balances, 'interval', seconds=CHAT_BALANCE_JOB_INTERVAL, args=(notify, ))
        scheduler.add_job(make_multisend_list_and_pay, 'interval', seconds=PAYMENT_JOB_INTERVAL)
        scheduler.add_job(local_chat_pay, 'interval', seconds=LOCAL_PAYMENT_JOB_INTERVAL)
        scheduler.start()
