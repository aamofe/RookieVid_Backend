# Generated by Django 3.2.5 on 2023-05-24 17:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0009_rename_status_favorite_is_private'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='comment_id',
            field=models.IntegerField(default=0, null=True, verbose_name='回复的评论ID'),
        ),
    ]
