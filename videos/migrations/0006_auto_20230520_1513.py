# Generated by Django 3.2.5 on 2023-05-20 07:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0005_favlist_user_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comment',
            name='reply_amount',
        ),
        migrations.RemoveField(
            model_name='video',
            name='comment_amount',
        ),
        migrations.RemoveField(
            model_name='video',
            name='fav_amount',
        ),
    ]