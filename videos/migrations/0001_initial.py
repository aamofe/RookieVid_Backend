# Generated by Django 3.2.5 on 2023-05-10 03:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0002_vcode'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(null=True, verbose_name='评论者ID')),
                ('video_id', models.IntegerField(null=True, verbose_name='被评论的视频ID')),
                ('content', models.CharField(max_length=255, verbose_name='评论内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='评论时间')),
            ],
        ),
        migrations.CreateModel(
            name='Like',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(null=True, verbose_name='点赞者ID')),
                ('video_id', models.IntegerField(null=True, verbose_name='被点赞的视频ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='点赞时间')),
            ],
        ),
        migrations.CreateModel(
            name='Reply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(null=True, verbose_name='回复者ID')),
                ('comment_id', models.IntegerField(null=True, verbose_name='所属评论ID')),
                ('content', models.CharField(max_length=255, verbose_name='回复内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='回复时间')),
            ],
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(default='娱乐', max_length=255, verbose_name='标签')),
                ('title', models.CharField(max_length=255, verbose_name='视频标题')),
                ('description', models.CharField(max_length=255, verbose_name='视频描述')),
                ('video', models.FileField(default='', upload_to='', verbose_name='视频')),
                ('cover', models.FileField(default='', upload_to='', verbose_name='封面')),
                ('video_url', models.CharField(default='', max_length=128, verbose_name='视频路径')),
                ('cover_url', models.CharField(default='', max_length=128, verbose_name='封面路径')),
                ('user_id', models.IntegerField(null=True, verbose_name='所属用户')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('reviewed_at', models.DateTimeField(null=True, verbose_name='审核时间')),
                ('reviewed_status', models.IntegerField(default=0, verbose_name='审核状态')),
                ('view_amount', models.IntegerField(default=0, verbose_name='播放量')),
                ('fav_amount', models.IntegerField(default=0, verbose_name='收藏量')),
                ('like_amount', models.IntegerField(default=0, verbose_name='点赞数')),
            ],
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=64, verbose_name='默认收藏夹')),
                ('description', models.TextField(verbose_name='描述')),
                ('status', models.IntegerField(default=0, verbose_name='是否为私有')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.user', verbose_name='收藏夹所属用户')),
            ],
        ),
        migrations.CreateModel(
            name='Favlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('favorite_id', models.IntegerField(default=0, verbose_name='收藏夹编号')),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='videos.video', verbose_name='')),
            ],
        ),
    ]
