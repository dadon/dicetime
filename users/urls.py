from django.urls import path
from dice_time.settings import API_TOKEN, ORIGIN
from . import views
from .bot import bot
from users.views import UsernameSelect2Autocomplete
bot.set_webhook(ORIGIN + 'tg/' + API_TOKEN)
urlpatterns = [
    path('tg/' + API_TOKEN, views.tg_webhook),
    path('username_select2/', UsernameSelect2Autocomplete.as_view(), name='username_select2'),


]
