# Generated by Django 2.1.7 on 2020-04-03 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20200402_0629'),
    ]

    operations = [
        migrations.AddField(
            model_name='texts',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='', verbose_name='Поле для видео'),
        ),
        migrations.AddField(
            model_name='tools',
            name='ms',
            field=models.IntegerField(default=0, verbose_name='Задержка между сообщениями цепочки в ms'),
        ),
    ]