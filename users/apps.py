import logging

from django.apps import AppConfig

logger = logging.getLogger('Dice')


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        logger.info('startup')
