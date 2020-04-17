import logging
import traceback
from datetime import datetime

from telebot import types
from django.views.decorators.csrf import csrf_exempt

from .bot import bot
from dal import autocomplete
from users.models import User, Service

from django.shortcuts import HttpResponse

from .tasks import tg_webhook_task

logger = logging.getLogger('Dice')


@csrf_exempt
def tg_webhook_celery(request):
    payload = request.body.decode("utf-8")
    service, _ = Service.objects.get_or_create(pk=1)
    tg_webhook_task.delay(payload, service.pending_updates_skip_until.timestamp())
    return HttpResponse('OK')


@csrf_exempt
def tg_webhook(request):
    try:
        service, _ = Service.objects.get_or_create(pk=1)
        payload = request.body.decode("utf-8")
        logger.debug(f'Update: {payload}')
        update = types.Update.de_json(payload)
        if update.message and datetime.utcfromtimestamp(update.message.date) <= service.pending_updates_skip_until:
            logger.info(f'#### Skipping this update')
            return HttpResponse('OK')
        bot.process_new_updates([update])
    except Exception as exc:
        logger.error(f'{type(exc)}: {exc}')
        logger.error(traceback.format_exc())

    return HttpResponse('OK')


class UsernameSelect2Autocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_staff:
            return User.objects.none()
        if not self.q:
            return User.objects.order_by('-date_reg')
        return (
            User.objects.filter(username__istartswith=self.q) |
            User.objects.filter(id__istartswith=self.q)
        ).order_by('-date_reg')[:10]
