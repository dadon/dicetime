import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from telebot import types
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.decorators import permission_required

from dice_time.settings import API_TOKEN, LOCAL, ORIGIN
from .bot import bot, scheduler
from dal import autocomplete
from users.models import User

from django.shortcuts import HttpResponse

from .tools import log_setup

log_setup(logging.DEBUG)

if LOCAL:
    bot.delete_webhook()
    time.sleep(1)
    scheduler.start()
    scheduler.print_jobs()
    bot.polling(none_stop=True, interval=1)
else:
    bot.set_webhook(ORIGIN + 'tg/' + API_TOKEN)



# Telegram Webhook handler
@csrf_exempt
def tg_webhook(request):
    bot.process_new_updates([ types.Update.de_json(request.body.decode("utf-8")) ])
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
