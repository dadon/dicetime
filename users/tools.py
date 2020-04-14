import logging
import sys
from functools import wraps

from logging.handlers import TimedRotatingFileHandler
from time import sleep
from typing import Union, Iterable, Callable

from dice_time.settings import LOCAL


def log_setup(loglevel=logging.INFO, loggers=['Dice', 'TeleBot']):
    log_fmt = '%(asctime)s (%(filename)s:%(lineno)d %(threadName)s) %(levelname)s - %(name)s: "%(message)s"'
    formatter = logging.Formatter(log_fmt)
    handlers = [logging.StreamHandler(sys.stdout)]
    if not LOCAL:
        handlers.append(TimedRotatingFileHandler(
            "debug.log", when='midnight', utc=True, backupCount=7))

    for h in handlers:
        h.setFormatter(formatter)
        for l_name in loggers:
            logger = logging.getLogger(l_name)
            logger.setLevel(loglevel)
            if l_name != 'TeleBot':
                logger.addHandler(h)



def retry(
        exceptions: Union[Exception, Iterable[Exception]], logger: Callable = print, tries=4, delay=3, backoff=2,
        default=None):
    """
    Retry calling the decorated function using an exponential backoff.

    :param exceptions: an exception (or iterable) to check  of exceptions)
    :param logger: <Callable> logger to use ('print' by default)
    :param tries: <int> number of times to try (not retry) before giving up
    :param delay: <int, float> initial delay between retries in seconds
    :param backoff: <int, float> backoff multiplier. For example, backoff=2 will make the delay x2 for each retry
    :param default: default value to return in case or error
    """
    exceptions = (exceptions, ) if not isinstance(exceptions, tuple) else exceptions
    logger_fn = logger if callable(logger) \
        else logger.info if isinstance(logger, logging.Logger) \
        else print

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            f_tries, f_delay = tries, delay
            while f_tries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{str(e)}, Retrying in {f_delay} seconds. fn: {f.__name__}\nargs: {args},\nkwargs: {kwargs}"
                    logger_fn(msg)
                    sleep(f_delay)
                    f_tries -= 1
                    f_delay *= backoff
            return default if default is not None else f(*args, **kwargs)
        return f_retry
    return deco_retry
