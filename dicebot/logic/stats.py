from decimal import Decimal

from django.db.models import Sum

from users.models import DiceEvent


def is_user_won(user, chat_id, date):
    return DiceEvent.objects \
        .filter(user=user, is_win=True, chat_id=chat_id, date__date=date) \
        .exists()


def get_user_won(user, date):
    user_agg = DiceEvent.objects \
        .values('user') \
        .filter(user=user, is_win=True, date__date=date, is_local=False) \
        .annotate(sum_user=Sum('summa'))
    return user_agg[0]['sum_user'] if user_agg else Decimal(0)


def get_user_won_by_chats(user, date, is_local=False, **params):
    user_agg = DiceEvent.objects \
        .values('chat_id') \
        .filter(
            user=user, is_win=True,
            date__date=date, is_local=is_local, **params) \
        .annotate(chat_sum_user=Sum('summa'))
    return user_agg


def get_chat_won(chat_id, date, is_local=False, **params):
    chat_stat = DiceEvent.objects \
        .filter(
            is_win=True,
            chat_id=chat_id, date__date=date, is_local=is_local, **params) \
        .aggregate(chat_sum=Sum('summa'))
    return chat_stat['chat_sum'] or Decimal(0)


def get_total_won_by_chats(date, is_local=False):
    chat_agg = DiceEvent.objects \
        .values('chat_id') \
        .filter(is_win=True, date__date=date, is_local=is_local) \
        .annotate(chat_sum=Sum('summa'))
    return {d['chat_id']: d['chat_sum'] for d in chat_agg}
