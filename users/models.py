from datetime import time
from decimal import Decimal

from django_pg_bulk_update import BulkUpdateManager
from encrypted_model_fields.fields import EncryptedTextField

from .fields import JSONField
from django.db import models


class Service(models.Model):
    pending_updates_skip_until = models.DateTimeField(null=True, default=None)


class AllowedChat(models.Model):
    chat_id = models.BigIntegerField(verbose_name='Chat ID')

    title_chat = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name='Имя чата')

    link_chat = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name='Юзернейм группы')

    registered_at = models.DateTimeField(
        verbose_name='Дата появления в БД',
        auto_now_add=True)
    created_at = models.DateTimeField(
        verbose_name='Дата создания чата',
        null=True, default=None)
    status = models.CharField(verbose_name='Статус', max_length=20, null=True, choices=(
        ('errored', 'Ошибка определения даты создания'),
        ('restricted', 'Группа запрещена'),
        ('activated', 'Группа разрешена')
    ), default=None)
    status_updated_at = models.DateTimeField(
        verbose_name='Дата последнего обновления статуса',
        null=True, default=None)
    creator = models.ForeignKey(
        'User', verbose_name='Создатель',
        on_delete=models.CASCADE, null=True)

    user_limit_day = models.DecimalField(
        decimal_places=6, max_digits=24,
        verbose_name='Лимит таймов на одного юзера, в день',
        default=0)
    chat_limit_day = models.DecimalField(
        decimal_places=6, max_digits=24,
        verbose_name='Лимит таймов на чат, в день',
        default=0)
    dice_time_from = models.TimeField(
        verbose_name='Dice Time (from)',
        default=time(hour=0, minute=0))
    dice_time_to = models.TimeField(
        verbose_name='Dice Time (to)',
        default=time(hour=23, minute=59, second=59))
    coin = models.CharField(
        verbose_name='Монета чата',
        default='TIME',
        max_length=10)

    def __str__(self):
        return f'Chat#{self.chat_id} {self.title_chat} status={self.status} status_updated_at={self.status_updated_at}'

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'


class Language(models.Model):
    name = models.CharField(max_length=30, verbose_name='Название языка')

    def __str__(self):
        return '{name}'.format(name=self.name)

    class Meta:
        verbose_name = 'Языки'
        verbose_name_plural = 'Языки'


class User(models.Model):
    id = models.BigIntegerField(verbose_name='ID в Телеграм', primary_key=True)
    first_name = models.CharField(verbose_name='Имя', max_length=255,blank=True,null=True)
    last_name = models.CharField(verbose_name='Фамилия', max_length=255,blank=True,null=True)
    username = models.CharField(
        verbose_name='Никнейм пользователя',
        max_length=60,
        blank=True,
        null=True)
    language = models.ForeignKey(
        Language,
        verbose_name='Язык',
        default=1,
        on_delete=models.CASCADE)
    date_reg = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата появления в боте')
    upvotes = models.PositiveIntegerField(verbose_name='Положительные отклики', default=0)
    downvotes = models.PositiveIntegerField(verbose_name='Отрицательные отклики', default=0)
    reply_count = models.PositiveIntegerField(verbose_name='Количество полученных reply', default=0)
    today_state = JSONField(
        verbose_name='Состояние юзера сегодня',
        default=dict)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return '{name} #{id}'.format(
            id=self.id, name=self.username or self.first_name)


class ChatWallet(models.Model):
    objects = BulkUpdateManager()

    chat = models.ForeignKey(
        AllowedChat,
        verbose_name='Чат',
        on_delete=models.CASCADE)
    address = models.CharField(
        max_length=42,
        verbose_name='Адрес (Mx...)',
        null=True, default=None)
    mnemonic = EncryptedTextField(
        verbose_name='Сид фраза', default='')
    balance = models.DecimalField(
        verbose_name='Баланс',
        decimal_places=6, max_digits=24,
        default=Decimal(0)
    )
    balance_updated_at = models.DateTimeField(
        verbose_name='Последнее обновление баланса',
        auto_now=True)

    def __str__(self):
        return '"{title}" chat wallet'.format(title=self.chat.title_chat)

    class Meta:
        verbose_name = 'Кошелек чата'
        verbose_name_plural = 'Кошельки чатов'


class MinterWallets(models.Model):
    objects = BulkUpdateManager()

    user = models.ForeignKey(
        User,
        verbose_name='Владелец кошелька',
        on_delete=models.CASCADE)
    address = models.CharField(
        max_length=42,
        verbose_name='Адрес (Mx...)')
    mnemonic = EncryptedTextField(
        verbose_name='Сид фраза')
    balance = models.DecimalField(
        verbose_name='Баланс',
        decimal_places=6, max_digits=24,
        default=Decimal(0)
    )
    balance_updated_at = models.DateTimeField(
        verbose_name='Последнее обновление баланса',
        auto_now=True)

    def __str__(self):
        return '{name}'.format(name=self.user)

    class Meta:
        verbose_name = 'Minter-Кошелек'
        verbose_name_plural = 'Minter-Кошельки'


class Tools(models.Model):
    address = models.CharField(
        verbose_name='Адрес выплат',
        max_length=42, default='')
    mnemonic = EncryptedTextField(
        verbose_name='Seed-фраза')
    payload = models.CharField(
        verbose_name='Payload при выводе средств из бота',
        default='',
        max_length=80)

    members_limit = models.PositiveIntegerField(
        verbose_name='Число участников, при котором можно считать чат "большим"',
        default=1000)
    user_limit_day = models.DecimalField(
        decimal_places=6, max_digits=24,
        verbose_name='Лимит таймов на одного юзера, в день',
        default=5)
    chat_limit_day = models.DecimalField(
        decimal_places=6, max_digits=24,
        verbose_name='Лимит таймов на чат, в день',
        default=200)
    total_limit_day = models.DecimalField(
        decimal_places=6, max_digits=24,
        verbose_name='Общий лимит таймов на всех, в день',
        default=4000)
        
    coin = models.CharField(
        verbose_name='Монета,в к-ой идет выплата',
        default='TIME',
        max_length=10)

    class Meta:
        verbose_name = 'Конфиг: выплаты, константы, параметры'


class DiceEvent(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь ТГ',
        on_delete=models.CASCADE)

    date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата event-a')

    chat_id = models.BigIntegerField(
        verbose_name='Chat ID совершенного event-a',
        default=1)

    summa = models.DecimalField(
        verbose_name='Cумма выигрыша',
        decimal_places=6, max_digits=24,
        default=Decimal(0))

    is_win = models.BooleanField(
        verbose_name='Победа',
        default=False)

    title_chat = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name='Имя чата')

    link_chat = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name='Юзернейм чата')
    
    is_payed = models.BooleanField(
        verbose_name='Отправлено на выплату',
        default=False)

    is_notified = models.BooleanField(
        verbose_name='Прислано уведомление об оплате',
        default=False)

    is_local = models.BooleanField(
        verbose_name='Локальный выигрыш',
        default=False)

    coin = models.CharField(
        max_length=10, verbose_name='Монета выигрыша', default='TIME')

    class Meta:
        verbose_name = 'Бросок кубика'
        verbose_name_plural = 'Броски кубика'

# Черный лист бота


class Exceptions(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE)

    def __str__(self):
        return f' {self.user}'

    class Meta:
        verbose_name = 'Blacklist'
        verbose_name_plural = 'Blacklist'


class Payment(models.Model):

    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE)

    event = models.ForeignKey(
        DiceEvent,
        null=True,
        verbose_name='Бросок кубика',
        on_delete=models.SET_NULL)

    to = models.CharField(
        max_length=85,
        verbose_name='Номер кошелька')

    amount = models.DecimalField(
        decimal_places=6, max_digits=24,
        verbose_name='Сумма на выплату',
        default=Decimal(0))

    coin = models.CharField(
        verbose_name='Монета,в к-ой идет выплата',
        default='-',
        max_length=10)
    
    is_payed = models.BooleanField(
        verbose_name='Оплачено',
        default=False)

    is_notified = models.BooleanField(
        verbose_name='Прислано уведомление об оплате',
        default=False)

    wallet_local = models.ForeignKey(
        ChatWallet,
        on_delete=models.CASCADE, null=True, default=None)
    
    def __str__(self):
        return f' {self.user}'

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'


class Text(models.Model):
    name = models.CharField(max_length=30, verbose_name='Название сообщения',default='Сообщение без номера')
    text_ru = models.TextField(verbose_name='Текст сообщения')
    text_eng = models.TextField(verbose_name='Текст сообщения eng')
    attachment = models.FileField(verbose_name='Поле для видео',blank=True,null=True)

    class Meta:
        verbose_name = 'Текст'
        verbose_name_plural = 'Тексты'


class Triggers(models.Model):
    phrase = models.CharField(max_length=30, verbose_name='Ключевая фраза')
    action = models.CharField(max_length=20, choices=(
        ('upvote', 'Повысить репутацию'),
        ('downvote', 'Понизить репутацию'),
        ('dice', 'Бросить кость')
    ), verbose_name='Действие')
    exact = models.BooleanField(verbose_name='Требует точного совпадения', default=False)

    def __str__(self):
        return f'"{self.phrase}" ({self.action})'

    class Meta:
        verbose_name = 'Триггер'
        verbose_name_plural = 'Триггеры'
