# Generated by Django 2.1.7 on 2020-04-05 09:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_auto_20200405_0845'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tools',
            name='main_value',
        ),
        migrations.AddField(
            model_name='tools',
            name='chat_limit_day',
            field=models.IntegerField(default=200, verbose_name='Лимит таймов на чат, в день'),
        ),
        migrations.AddField(
            model_name='tools',
            name='total_limit_day',
            field=models.IntegerField(default=4000, verbose_name='Общий лимит таймов на всех, в день'),
        ),
        migrations.AddField(
            model_name='tools',
            name='user_limit_day',
            field=models.IntegerField(default=5, verbose_name='Лимит таймов на одного юзера, в день'),
        ),
    ]
