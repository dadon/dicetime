# Generated by Django 2.1.7 on 2020-04-15 10:16

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_auto_20200414_1809'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Texts',
            new_name='Text',
        ),
        migrations.AlterField(
            model_name='allowedchat',
            name='dice_time_to',
            field=models.TimeField(default=datetime.time(23, 59, 59), verbose_name='Dice Time (to)'),
        ),
    ]
