import csv

from django.contrib import admin
from django import forms
from dal import autocomplete
from django.http import HttpResponse

from .models import *


class ExceptionsForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=autocomplete.ModelSelect2(url='username_select2')
    )

    class Meta:
        model = Exceptions
        fields = ('__all__')


@admin.register(Exceptions)
class ExceptionsAdmin(admin.ModelAdmin):
    form = ExceptionsForm
    list_display = ('user',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'first_name', 'last_name', 'username')
    search_fields = ['id', 'first_name', 'last_name', 'username']


@admin.register(MinterWallets)
class WalletAdmin(admin.ModelAdmin):

    list_display = ('user', 'address', 'balance', 'balance_updated_at')
    search_fields = ['user', 'address', 'balance', 'balance_updated_at']


@admin.register(Tools)
class ToolsAdmin(admin.ModelAdmin):
    list_display = (
        'address', 'payload', 'coin',
        'members_limit', 'user_limit_day', 'chat_limit_day', 'total_limit_day')


@admin.register(DiceEvent)
class DiceEventAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'date', 'coin', 'summa', 'is_local', 'is_win', 'is_payed',
        'chat_id', 'title_chat', 'link_chat',
    )
    search_fields = ['chat_id', 'user', 'date', 'title_chat']


@admin.register(Text)
class TextsAdmin(admin.ModelAdmin):
    list_display_links = None
    list_display = ('name', 'text_ru', 'text_eng')
    list_editable = ['name', 'text_ru', 'text_eng']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Triggers)
class TriggersAdmin(admin.ModelAdmin):
    list_display_links = None
    list_display = 'phrase', 'action', 'exact'
    list_editable = 'phrase', 'action', 'exact'


@admin.register(AllowedChat)
class ChatAdmin(admin.ModelAdmin):
    list_display = 'chat_id', 'title_chat', 'link_chat', 'status', 'creator'
    actions = ["export_as_csv"]
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"
