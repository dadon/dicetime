import logging

from django.core.management.base import BaseCommand
from mintersdk.sdk.wallet import MinterWallet

from users.models import Tools

from users.tools import log_setup

logger = logging.getLogger('Dice')
log_setup(logging.DEBUG)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('mnemonic', nargs='+', type=str)

    def handle(self, **options):
        mnemonic = ' '.join(options.get('mnemonic', [])) or None

        mdl = Tools.objects.first()
        if mdl:
            mdl.delete()

        wallet = MinterWallet.create(mnemonic=mnemonic)
        Tools.objects.create(
            mnemonic=mnemonic,
            address=wallet['address'])

