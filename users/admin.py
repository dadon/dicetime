from django.contrib import admin
from .models import *


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    list_display = ('id', 'first_name', 'last_name', 'username')

    search_fields = ['id', 'first_name', 'last_name', 'username']


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):

    list_display = ('name',)

    search_fields = ['name']


@admin.register(MinterWallets)
class PrizmWalletAdmin(admin.ModelAdmin):

    list_display = ('user', 'number',)

    search_fields = ['user', 'number']


@admin.register(Triggers)
class TriggersAdmin(admin.ModelAdmin):

    list_display = ('name',)

    search_fields = ['name']


@admin.register(Tools)
class ToolsAdmin(admin.ModelAdmin):
    pass


@admin.register(DiceEvent)
class DiceEventAdmin(admin.ModelAdmin):
    pass
