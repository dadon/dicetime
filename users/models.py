from decimal import Decimal

from django.contrib.postgres.fields import JSONField
from django.db import models
import datetime
from datetime import date


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
    date_reg = models.DateField(
        auto_now_add=True,
        verbose_name='Дата появления в боте')
    warned_today = models.SmallIntegerField(
        verbose_name='Сколько раз предупрежден о лимитах (на сегодня)',
        default=0)
    warned_chats = JSONField(
        verbose_name='Сколько раз предупрежден о лимитах (чаты)',
        default={})

    def __str__(self):
        return '{name} #{id}'.format(
            id=self.id, name=self.username or self.first_name)

    class Meta:
        verbose_name = 'Пользователь Telegram'
        verbose_name_plural = 'Пользователи Telegram'


class MinterWallets(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Владелец кошелька',
        on_delete=models.CASCADE)
    number = models.CharField(
        max_length=85,
        blank=True,
        null=True,
        verbose_name='Номер кошелька')
    mnemonic = models.TextField(verbose_name='Сид фраза кошелька')

    def __str__(self):
        return '{name}'.format(name=self.user)

    class Meta:
        verbose_name = 'М-Кошельки пользователей'
        verbose_name_plural = 'М-Кошельки пользователей'


class Tools(models.Model):

    ms = models.FloatField(verbose_name='Задержка между сообщениями цепочки в seconds', 
        default=0)
    join = models.TextField(verbose_name='Seed-фраза')
    payload = models.CharField(
        verbose_name='Payload при выводе средств из бота',
        default='-',
        max_length=80)

    user_limit_day = models.IntegerField(
        verbose_name='Лимит таймов на одного юзера, в день',
        default=5)
    chat_limit_day = models.IntegerField(
        verbose_name='Лимит таймов на чат, в день',
        default=200)
    total_limit_day = models.IntegerField(
        verbose_name='Общий лимит таймов на всех, в день',
        default=4000)
        
    coin = models.CharField(
        verbose_name='Монета,в к-ой идет выплата',
        default='-',
        max_length=10)

    class Meta:

        verbose_name = 'Настройки выплат'
        verbose_name_plural = 'Настройки выплат'


class DiceEvent(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь ТГ',
        on_delete=models.CASCADE)

    date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата event-a')

    chat_id = models.IntegerField(
        verbose_name='Id-чата совершенного event-a',
        default=1)

    summa = models.DecimalField(
        decimal_places=6, max_digits=24,
        verbose_name='Cумма выигрыша',
        default=Decimal(0))

    is_win = models.BooleanField(
        verbose_name='Выиграл?',
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
        verbose_name='Линк на чат')
    
    is_payed = models.BooleanField(
        verbose_name='Отправлено на выплату?',
        default=False)

    is_notified = models.BooleanField(
        verbose_name='Отправлено на выплату?',
        default=False)

    class Meta:
        verbose_name = 'События'
        verbose_name_plural = 'События'

# Черный лист бота


class Exceptions(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь ТГ',
        on_delete=models.CASCADE)

    def __str__(self):
        return f' {self.user}'

    class Meta:
        verbose_name = 'Бан-лист'
        verbose_name_plural = 'Бан-лист'


class Payment(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь ТГ',
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
        verbose_name='сумма на выплату',
        default=Decimal(0))

    coin = models.CharField(
        verbose_name='Монета,в к-ой идет выплата',
        default='-',
        max_length=10)
    
    is_payed = models.BooleanField(
        verbose_name='Оплачено?',
        default=False)

    is_notified = models.BooleanField(
        verbose_name='Прислано уведомление об оплате',
        default=False)
    
    def __str__(self):
        return f' {self.user}'

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платеж'


class Texts(models.Model):
    name = models.CharField(max_length=30, verbose_name='Название сообщения',default='Сообщение без номера')
    text_ru = models.TextField(verbose_name='Текст сообщения')
    text_eng = models.TextField(verbose_name='Текст сообщения eng')
    attachment = models.FileField(verbose_name='Поле для видео',blank=True,null=True)

    class Meta:
        verbose_name = 'Текста'
        verbose_name_plural = 'Текста в боте'


class Triggers(models.Model):
    name = models.CharField(max_length=30, verbose_name='Название метки')

    def __str__(self):
        return '{name}'.format(name=self.name)

    class Meta:
        verbose_name = 'Триггеры'
        verbose_name_plural = 'Триггеры'
