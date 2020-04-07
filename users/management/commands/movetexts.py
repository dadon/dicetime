from django.core.management.base import BaseCommand

from users.models import Texts


class Command(BaseCommand):
    def handle(self, **options):
        texts = Texts.objects.using('sqlite').all()
        Texts.objects.bulk_create(texts)
