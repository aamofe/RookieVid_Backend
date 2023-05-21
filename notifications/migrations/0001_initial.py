# Generated by Django 4.1.7 on 2023-05-21 11:22

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('send_to', models.IntegerField(verbose_name='通知对象ID')),
                ('send_from', models.IntegerField(default=0, verbose_name='通知者ID')),
                ('title', models.CharField(max_length=64, verbose_name='通知标题')),
                ('content', models.CharField(max_length=255, verbose_name='通知内容')),
                ('link_type', models.IntegerField(default=0, verbose_name='通知类型')),
                ('link_id', models.IntegerField(default=0, verbose_name='关联视频/评论ID')),
                ('is_read', models.BooleanField(default=False, verbose_name='是否已读')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='通知创建时间')),
            ],
        ),
    ]
