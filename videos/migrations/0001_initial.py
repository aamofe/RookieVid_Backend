# Generated by Django 3.2.9 on 2023-05-01 10:16

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20, verbose_name='分类名称')),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(verbose_name='评论者ID')),
                ('video_id', models.IntegerField(verbose_name='被评论的视频ID')),
                ('content', models.CharField(max_length=255, verbose_name='评论内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='评论时间')),
            ],
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(verbose_name='收藏者ID')),
                ('video_id', models.IntegerField(verbose_name='被收藏的视频ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='收藏时间')),
            ],
        ),
        migrations.CreateModel(
            name='Like',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(verbose_name='点赞者ID')),
                ('video_id', models.IntegerField(verbose_name='被点赞的视频ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='点赞时间')),
            ],
        ),
        migrations.CreateModel(
            name='Reply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(verbose_name='回复者ID')),
                ('comment_id', models.IntegerField(verbose_name='所属评论ID')),
                ('content', models.CharField(max_length=255, verbose_name='回复内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='回复时间')),
            ],
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(default='娱乐', max_length=255, verbose_name='标签')),
                ('title', models.CharField(max_length=20, verbose_name='视频标题')),
                ('description', models.CharField(max_length=255, verbose_name='视频描述')),
                ('video_path', models.CharField(max_length=255, null=True, verbose_name='视频地址')),
                ('cover_path', models.CharField(max_length=255, null=True, verbose_name='封面地址')),
                ('user_id', models.IntegerField(verbose_name='视频创建者ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('reviewed_at', models.DateTimeField(null=True, verbose_name='审核时间')),
                ('reviewed_status', models.IntegerField(default=0, verbose_name='审核状态')),
                ('reviewed_result', models.IntegerField(default=0, verbose_name='审核结果')),
                ('reviewed_reason', models.CharField(max_length=255, verbose_name='审核原因')),
                ('play_amount', models.IntegerField(default=0, verbose_name='播放量')),
            ],
        ),
    ]
