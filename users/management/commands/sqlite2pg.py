from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import Text, User, Language, Tools, MinterWallets, Triggers


@transaction.atomic
def delete_create(model):
    models = model.objects.using('sqlite').all()
    model.objects.all().delete()
    model.objects.bulk_create(models)


class Command(BaseCommand):
    def handle(self, **options):
        for m in [Text, Language, Tools, Triggers]:
            delete_create(m)
