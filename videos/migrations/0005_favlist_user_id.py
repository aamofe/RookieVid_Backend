# Generated by Django 3.2.5 on 2023-05-19 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0004_reply_video_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='favlist',
            name='user_id',
            field=models.IntegerField(null=True, verbose_name='所属用户'),
        ),
    ]