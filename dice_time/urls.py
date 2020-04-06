from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from dice_time.settings import LOCAL, ORIGIN, API_TOKEN
from dice_time.wsgi import scheduler
from users.bot import bot

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


@scheduler.scheduled_job('date')
def bot_start():
    if LOCAL:
        bot.delete_webhook()
        bot.polling(none_stop=True, interval=0)
    else:
        wh = bot.get_webhook_info()
        if wh.pending_update_count:
            bot.delete_webhook()
            bot.skip_updates()
        bot.set_webhook(ORIGIN + 'tg/' + API_TOKEN)
