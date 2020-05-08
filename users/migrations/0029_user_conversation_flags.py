# Generated by Django 2.2.12 on 2020-05-06 20:31

from django.db import migrations
import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0028_chatmember'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='conversation_flags',
            field=users.fields.JSONField(default=dict, verbose_name='Флаги состояния переписки'),
        ),
    ]