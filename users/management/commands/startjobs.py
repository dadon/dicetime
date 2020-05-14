from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management.base import BaseCommand
from pyrogram import Client

from dice_time.settings import TG_API_ID, TG_API_HASH, API_TOKEN
from dicebot.logic.jobs import update_balances, USER_BALANCE_JOB_INTERVAL, CHAT_BALANCE_JOB_INTERVAL, \
    PAYMENT_JOB_INTERVAL, LOCAL_PAYMENT_JOB_INTERVAL, make_multisend_list_and_pay, local_chat_pay

from users.models import MinterWallets, ChatWallet


def update_user_balances(app):
    update_balances(app, MinterWallets)


def update_chat_balances(app, notify):
    update_balances(app, ChatWallet, notify=notify)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--notify', default='on')

    def handle(self, **options):
        notify = options['notify'] == 'on'

        scheduler = BackgroundScheduler()

        client = Client(
            'session_jobs', api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=API_TOKEN, no_updates=True)
        client.start()

        scheduler.add_job(update_user_balances, 'interval', seconds=USER_BALANCE_JOB_INTERVAL, args=(client, ))
        scheduler.add_job(update_chat_balances, 'interval', seconds=CHAT_BALANCE_JOB_INTERVAL, args=(client, notify))
        scheduler.add_job(make_multisend_list_and_pay, 'interval', seconds=PAYMENT_JOB_INTERVAL)
        scheduler.add_job(local_chat_pay, 'interval', seconds=LOCAL_PAYMENT_JOB_INTERVAL)

        scheduler.start()
        Client.idle()

        scheduler.shutdown()
        client.stop()
