# Generated by Django 3.2.9 on 2023-05-23 06:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0008_favorite_cover_url'),
    ]

    operations = [
        migrations.RenameField(
            model_name='favorite',
            old_name='status',
            new_name='is_private',
        ),
    ]
