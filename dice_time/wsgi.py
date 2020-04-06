"""
WSGI config for dice_time project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""
import logging
import os

from django.core.wsgi import get_wsgi_application
from users.bot import scheduler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dice_time.settings')

logger = logging.getLogger('Dice')

scheduler.start()
logger.info('------------ JOBS')
scheduler.print_jobs()
logger.info('------------ JOBS')

application = get_wsgi_application()
