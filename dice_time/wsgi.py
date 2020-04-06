"""
WSGI config for dice_time project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dice_time.settings')

logger = logging.getLogger('Dice')
scheduler = BackgroundScheduler()
scheduler.start()


application = get_wsgi_application()
