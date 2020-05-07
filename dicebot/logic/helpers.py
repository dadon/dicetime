import logging
from decimal import Decimal, ROUND_DOWN
from functools import wraps
from time import sleep
from typing import Union, Iterable, Callable


def normalize_text(text):
    """
    lower + remove multiple spaces + strip
    """
    return ' '.join(filter(None, str(text).lower().split(' '))).strip()


def truncate(number, rounding):
    if isinstance(number, float):
        number = Decimal(number)
    if isinstance(number, Decimal):
        return number.quantize(Decimal(f'0.{"1"*rounding}'), rounding=ROUND_DOWN)
    return number


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

