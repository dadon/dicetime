import logging
import sys

from logging.handlers import TimedRotatingFileHandler
from dice_time.settings import LOCAL

logger = logging.getLogger('Dice')


def log_setup(loglevel=logging.INFO):
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handlers = [logging.StreamHandler(sys.stdout)]
    if not LOCAL:
        handlers.append(TimedRotatingFileHandler(
            "debug.log", when='midnight', utc=True, backupCount=7))

    for h in handlers:
        h.setFormatter(formatter)
        logger.addHandler(h)

    logger.setLevel(loglevel)
    logging.getLogger('TeleBot').setLevel(loglevel)

