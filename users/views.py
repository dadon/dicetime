import logging

from telebot import types
from django.views.decorators.csrf import csrf_exempt

from .bot import bot
from dal import autocomplete
from users.models import User

from django.shortcuts import HttpResponse

logger = logging.getLogger('Dice')


# Telegram Webhook handler
@csrf_exempt
def tg_webhook(request):
    update = types.Update.de_json(request.body.decode("utf-8"))
    if update.update_id <= bot.last_update_id:
        logger.info(f'Skipping update: {request.body.decode("utf-8")}')
        return HttpResponse('OK')
    bot.process_new_updates([update])
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
