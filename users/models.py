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
    is_bot = models.BooleanField(verbose_name='Статус бота', default=False)
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

    main_value = models.IntegerField(
        verbose_name='Число для расчета в формуле выплат', 
        default=3)
        
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

    summa = models.PositiveIntegerField(
        verbose_name='Cумма выигрыша',
        default=0)

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
        verbose_name='Оплачено?',
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
