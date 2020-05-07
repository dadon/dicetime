import os
import django
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dice_time.settings')
django.setup()


app = Celery('dicetime')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(['dicebot.logic'])
