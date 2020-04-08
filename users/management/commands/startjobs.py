import logging

from django.core.management.base import BaseCommand
from mintersdk.sdk.wallet import MinterWallet

from dice_time.settings import LOCAL, ORIGIN, API_TOKEN
from users.bot import send, multisend
from users.models import Payment, Tools
from apscheduler.schedulers.blocking import BlockingScheduler

from users.tools import log_setup

scheduler = BlockingScheduler()
logger = logging.getLogger('Dice')
log_setup(logging.DEBUG)


@scheduler.scheduled_job('date')
def bot_run():
    from users.bot import bot

    if LOCAL:
        logger.info('Start polling (LOCAL=True)')
        bot.delete_webhook()
        bot.polling(none_stop=True, interval=0)
    else:
        wh = bot.get_webhook_info()
        if wh.pending_update_count:
            bot.delete_webhook()
            bot.skip_updates()
        logger.info('Start webhook (LOCAL=False)')
        bot.set_webhook(ORIGIN + 'tg/' + API_TOKEN)


@scheduler.scheduled_job('interval', minutes=1)
def make_multisend_list_and_pay():
    LIMIT=75
    multisend_list = []
    gifts = Payment.objects.filter(is_payed=False)[:LIMIT]

    if not gifts:
        logger.info(f'No events to pay')
        return

    settings = Tools.objects.get(pk=1)
    wallet_from = MinterWallet.create(mnemonic=settings.join)

    if len(gifts) == 1:
        g = gifts[0]
        send(wallet_from, g.to, g.coin, g.amount, gas_coin=g.coin, payload=settings.payload)
        g.is_payed = True
        g.save()
        return

    for g in gifts:
        multisend_list.append({'coin': g.coin, 'to': g.to, 'value': g.amount})
        g.is_payed = True
        g.save()

    multisend(wallet_from=wallet_from, w_dict=multisend_list, gas_coin=settings.coin, payload=settings.payload)


class Command(BaseCommand):
    def handle(self, **options):
        scheduler.start()
