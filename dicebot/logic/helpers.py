import logging
from decimal import Decimal, ROUND_DOWN
from functools import wraps
from time import sleep
from typing import Union, Iterable, Callable

from dicebot.logic.telegram import get_full_user


def parse_drop_coins(message):
    text = message.text
    msg_parts = list(filter(None, str(text).lower().split(' ')))
    if not msg_parts or len(msg_parts) < 2 or msg_parts[0] != 'drop':
        return

    try:
        total = float(msg_parts[1])
    except Exception:
        return

    coin = 'TIME' if len(msg_parts) == 2 else msg_parts[2].upper()
    mode = 'next' if len(msg_parts) <= 3 else msg_parts[3]
    params = msg_parts[4:]
    return total, coin, mode, params


def parse_send_coins(app, message):
    text = message.text
    msg_parts = list(filter(None, str(text).lower().split(' ')))
    if not msg_parts or len(msg_parts) < 2 or msg_parts[0] != 'send':
        return

    try:
        amount = float(msg_parts[1])
    except Exception:
        return

    coin = 'TIME' if len(msg_parts) == 2 else msg_parts[2].upper()
    recipients = []
    for entity in message.entities or []:
        if entity.type == 'mention':
            username = message.text[entity.offset:entity.offset + entity.length]
            user_full = get_full_user(app, username)
            if user_full:
                recipients.append(user_full.user)
            continue
        if entity.type == 'text_mention':
            recipients.append(entity.user)
    return amount, coin, recipients


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

