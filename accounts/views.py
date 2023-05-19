import time
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import AnonymousUser
from decorator.decorator_permission import validate_login, validate_all
from django.http import JsonResponse
from django.core.mail import send_mail
from RookieVid_Backend import settings
from videos.cos_utils import get_cos_client
from videos.models import Video, Favorite, Favlist
from accounts.models import User, Follow, Vcode
from notifications.views import send_sys_notification
from notifications.models import Notification
import uuid
import os
import jwt
import re
import random
from django.utils import timezone
from datetime import datetime, timedelta

# Create your views here.

# 发送验证码
@csrf_exempt
def send_vcode(request):
    if request.method == 'POST':
        to_email = request.POST.get("email")
        print("to_email : ", to_email)
        if re.match('\w+@\w+.\w+', str(to_email)) is None:
            return JsonResponse({'errno': 0, 'msg': "邮箱格式错误"})
        # 通过邮箱判断用户是否已存在
        if User.objects.filter(email=to_email).exists():
            return JsonResponse({'errno': 0, 'msg': "邮箱已占用，请更换邮箱地址"})

        # 获取当前时间
        now_time = timezone.now()
        # 获取上次发送邮件的时间
        if Vcode.objects.filter(to_email=to_email).exists():
            codes = Vcode.objects.filter(to_email=to_email)
            for vcode in codes:
                if (now_time - vcode.send_at).seconds < 60:  # 1分钟内不能重复发送邮件
                    return JsonResponse({'errno': 0, 'msg': "操作过于频繁，请稍后再试"})
        # 随机生成一个新的验证码
        code = str(random.randint(10 ** 5, 10 ** 6 - 1))
        while Vcode.objects.filter(vcode=code).exists():
            code = str(random.randint(10 ** 5, 10 ** 6 - 1))
        EMAIL_FROM = "1151801165@qq.com"  # 邮箱来自
        email_title = '邮箱激活'
        email_body = "您的邮箱注册验证码为：{}, 该验证码有效时间为5分钟，请及时进行验证。".format(code)
        send_errno = send_mail(email_title, email_body, EMAIL_FROM, [to_email])
        if send_errno == 1:
            # 存储验证码
            new_vcode = Vcode(vcode=code, to_email=to_email)
            new_vcode.save()
            return JsonResponse({'errno': 0, 'msg': '验证码已发送，请查阅'})
        else:
            return JsonResponse(
                {'from': EMAIL_FROM, 'to': to_email, 'errno': 0, 'msg': "验证码发送失败，请检查邮箱地址"})
    else:
        return JsonResponse({'error': 0, 'msg': "请求方式错误"})


# 先验证验证码是否正确，若正确检验用户名密码是否合法，完成注册
@csrf_exempt
def register(request):
    if request.method == 'POST':  # 判断请求方式是否为 POST（要求POST方式）
        # 获取输入的验证码和邮箱
        email = request.POST.get('email')
        vcode = request.POST.get('vcode')

        # 判断验证码是否失效
        now_time = timezone.now()
        # 获取发送验证码时间
        if Vcode.objects.filter(to_email=email).exists():
            if Vcode.objects.filter(vcode=vcode).exists():
                code = Vcode.objects.get(vcode=vcode)
                if (now_time - code.send_at).seconds <= 300:
                    code.delete()
                else:
                    # 该邮箱获取的验证码均已失效，删除
                    codes = Vcode.objects.filter(to_email=email)
                    for code in codes:
                        code.delete()
                    return JsonResponse({'errno': 0, 'msg': '验证码失效，请重新获取'})
            else:
                return JsonResponse({'errno': 0, 'msg': '验证码错误'})
        else:
            return JsonResponse({'errno': 0, 'msg': '该账户没有获取验证码'})

        # 验证码正确，进行注册
        username = request.POST.get('username')  # 获取请求数据
        password_1 = request.POST.get('password_1')
        password_2 = request.POST.get('password_2')

        # 用户名长度为1-20位
        if re.match('.{1,20}', str(username)) is None:
            return JsonResponse({'errno': 0, 'msg': "用户名不合法"})
        # 密码长度为8-16位，且同时包含数字和字母
        if re.match('(?!^[0-9]+$)(?!^[a-zA-Z]+$)[0-9A-Za-z]{8,16}', str(password_1)) is None:
            return JsonResponse({'username': username, 'password': password_1, 'errno': 0, 'msg': "密码格式错误"})
        if password_1 != password_2:
            return JsonResponse({'errno': 0, 'msg': "两次输入的密码不同"})
        else:
            # 为用户分配不重复的uid
            uid = str(random.randint(10 ** 9, 10 ** 10 - 1))
            while User.objects.filter(uid=uid).exists():
                uid = str(random.randint(10 ** 9, 10 ** 10 - 1))
            # 数据库存取：新建 User 对象，赋值并保存
            new_user = User(uid=uid, username=username, password=password_1, email=email)
            new_user.save()  # 一定要save才能保存到数据库中
            return JsonResponse({'uid': uid, 'errno': 0, 'msg': "注册成功"})
    else:
        return JsonResponse({'error': 0, 'msg': "请求方式错误"})


@csrf_exempt
def login(request):
    if request.method == 'POST':
        uid = request.POST.get('uid')  # 获取请求数据
        password = request.POST.get('password')
        if User.objects.filter(uid=uid).exists():
            user = User.objects.get(uid=uid)
        elif User.objects.filter(email=uid).exists():
            user = User.objects.get(email=uid)
        else:
            return JsonResponse({'errno': 0, 'msg': "请先注册"})
        if user.password == password:  # 判断请求的密码是否与数据库存储的密码相同
            # request.session['id'] = user.uid
            payload = {'exp': datetime.utcnow()+timedelta(days=2), 'id': user.id}
            encode = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256').decode()
            # token = str(encode, encoding='utf-8')
            token = str(encode)
            print(encode)
            return JsonResponse({'token': token, 'status': user.status, 'errno': 0, 'msg': "登录成功"})
        else:
            return JsonResponse({'errno': 0, 'msg': "密码错误"})
    else:
        return JsonResponse({'error': 0, 'msg': "请求方式错误"})


@csrf_exempt
def logout(request):
    request.session.flush()
    return JsonResponse({'errno': 0, 'msg': "注销成功"})


def upload_photo_method(photo_file, photo_id):
    client, bucket_name, bucket_region = get_cos_client()

    if photo_id == '' or photo_id == 0:
        photo_id = str(uuid.uuid4())
    photo_key = "avatar_file/{}".format(f'{photo_id}.png')
    response_photo = client.put_object(
        Bucket=bucket_name,
        Body=photo_file,
        Key=photo_key,
        StorageClass='STANDARD',
        ContentType="image/png"
    )
    photo_url = ""
    if 'url' in response_photo:
        photo_url = response_photo['url']
    else:
        photo_url = f'https://{bucket_name}.cos.{bucket_region}.myqcloud.com/{photo_key}'
    return photo_url


@csrf_exempt
@validate_login
def display_profile(request):
    # 如果用户已登录，展示用户信息
    if request.method == 'GET':
        user = request.user
        context = User.to_dict(user)
        return JsonResponse({'context': context, 'errno': 0, 'msg': '查询用户信息成功'})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方式错误"})


@csrf_exempt
@validate_login
def edit_profile(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        signature = request.POST.get('signature')
        # 能不能有自动填入之类的（？
        if re.match('.{1,20}', str(username)) is None:
            return JsonResponse({'errno': 0, 'msg': "用户名不合法"})
        user = request.user
        user.username = username
        user.signature = signature
        # 上传头像单独写
        user.save()
        return JsonResponse({'errno': 0, 'msg': "用户资料修改成功"})
    else:
        return JsonResponse({'error': 0, 'msg': "请求方式错误"})


@csrf_exempt
@validate_login
def edit_avatar(request):
    if request.method == 'POST':
        user = request.user
        avatar_file = request.FILES.get('avatar_file')
        avatar_url = upload_photo_method(avatar_file, user.uid)  # 头像的命名还是用uid
        user.avatar_url = avatar_url
        user.save()
        return JsonResponse({'errno': 0, 'msg': "头像上传成功"})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方式错误"})


@csrf_exempt
@validate_login
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        password_1 = request.POST.get('password_1')
        password_2 = request.POST.get('password_2')
        user = request.user
        if old_password != user.password:
            return JsonResponse({'errno': 0, 'msg': "密码错误，请重新输入"})
        if re.match('(?!^[0-9]+$)(?!^[a-zA-Z]+$)[0-9A-Za-z]{8,16}', str(password_1)) is None:
            return JsonResponse({'password': password_1, 'errno': 0, 'msg': "密码格式错误"})
        if password_1 != password_2:
            return JsonResponse({'errno': 0, 'msg': "两次输入的密码不同"})
        user.password = password_1
        user.save()
        return JsonResponse({'errno': 0, 'msg': "密码修改成功"})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方式错误"})


@csrf_exempt
@validate_login
def change_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        vcode = request.POST.get('vcode')
        # 判断验证码
        now_time = timezone.now()
        if Vcode.objects.filter(to_email=email).exists():
            if Vcode.objects.filter(vcode=vcode).exists():
                code = Vcode.objects.get(vcode=vcode)
                if (now_time - code.send_at).seconds <= 300:
                    code.delete()
                else:
                    # 该邮箱获取的验证码均已失效，删除
                    codes = Vcode.objects.filter(to_email=email)
                    for code in codes:
                        code.delete()
                    return JsonResponse({'errno': 0, 'msg': '验证码失效，请重新获取'})
            else:
                return JsonResponse({'errno': 0, 'msg': '验证码错误'})
        else:
            return JsonResponse({'errno': 0, 'msg': '该账户没有获取验证码'})

        user = request.user
        user.email = email
        user.save()
        return JsonResponse({'errno': 0, 'msg': '绑定邮箱修改成功'})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方式错误"})


@csrf_exempt
@validate_login
def create_follow(request):
    if request.method == 'POST':
        following_id = request.POST.get('following_id')  # 这里传入参数改成user.id
        try:
            User.objects.get(id=following_id)
        except User.DoesNotExist:
            return JsonResponse({'errno': 0, 'msg': "用户不存在"})
        follower_id = request.user.id
        follower_user = request.user.username
        follow = Follow(follower_id=follower_id, following_id=following_id)
        follow.save()
        send_sys_notification('系统通知', following_id, f'{follower_user}关注了你')
        resp = {'follower': follower_id, 'following': following_id, 'errno': 0, 'msg': '关注成功'}
        return JsonResponse(resp)
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方式错误"})


@csrf_exempt
@validate_login
def remove_follow(request):
    if request.method == 'POST':
        following_id = request.POST.get('following_id')  # 传入参数改成user.id
        follower_id = request.user.id
        follow = Follow.objects.get(follower_id=follower_id, following_id=following_id)
        follow.delete()
        resp = {'follower': follower_id, 'following': following_id, 'errno': 0, 'msg': '取关成功'}
        return JsonResponse(resp)
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方式错误"})


@csrf_exempt
@validate_login
def get_followings(request):
    if request.method == 'GET':
        following_list = []
        user_id = request.user.id
        if Follow.objects.filter(follower_id=user_id).exists():
            followings = Follow.objects.filter(follower_id=user_id)
            for following in followings:
                following_user = User.objects.get(id=following.following_id)
                following_data = User.to_simple_dict(following_user)
                following_list.append(following_data)
            return JsonResponse({'errno': 0, 'msg': "关注列表查询成功", 'data': following_list})
        else:
            return JsonResponse({'errno': 0, 'msg': "关注列表为空", 'data': following_list})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方法错误"})


@csrf_exempt
@validate_login
def get_followers(request):
    if request.method == 'GET':
        follower_list = []
        user_id = request.user.id
        if Follow.objects.filter(following_id=user_id).exists():
            followers = Follow.objects.filter(following_id=user_id)
            for follower in followers:
                follower_user = User.objects.get(id=follower.follower_id)
                follower_data = User.to_simple_dict(follower_user)
                follower_list.append(follower_data)
            return JsonResponse({'errno': 0, 'msg': "粉丝列表查询成功", 'data': follower_list})
        else:
            return JsonResponse({'errno': 0, 'msg': "粉丝列表为空", 'data': follower_list})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方法错误"})


@csrf_exempt
@validate_all
def get_videos(request):
    if request.method == 'GET':
        video_list = []
        user_id = request.GET.get('user_id')
        if Video.objects.filter(user_id=user_id).exists():
            videos = Video.objects.filter(user_id=user_id)
            for video in videos:
                video_data = Video.to_simple_dict(video)
                video_list.append(video_data)
            return JsonResponse({'errno': 0, 'msg': "投稿列表查询成功", 'data': video_list})
        else:
            return JsonResponse({'errno': 0, 'msg': "投稿列表为空", 'data': video_list})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方法错误"})


@csrf_exempt
@validate_login
def get_favorites(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        favorite_list = []
        uid = request.user.uid
        if uid == user_id:
            if Favorite.objects.filter(user_id=uid).exists():
                favorites = Favorite.objects.filter(user_id=uid)
                for favorite in favorites:
                    favorite_data = Favorite.to_dict(favorite)
                    favorite_list.append(favorite_data)
                return JsonResponse({'errno': 0, 'msg': "收藏夹列表查询成功", 'data': favorite_list})
            else:
                return JsonResponse({'errno': 0, 'msg': "收藏夹列表为空", 'data': favorite_list})
        else:
            if Favorite.objects.filter(user_id=user_id).exists():
                favorites = Favorite.objects.filter(user_id=user_id)
                for favorite in favorites:
                    if favorite.status == 0:
                        favorite_data = Favorite.to_dict(favorite)
                        favorite_list.append(favorite_data)
                if len(favorite_list) == 0:
                    return JsonResponse({'errno': 0, 'msg': "收藏夹列表为空", 'data': favorite_list})
                else:
                    return JsonResponse({'errno': 0, 'msg': "收藏夹列表查询成功", 'data': favorite_list})
            else:
                return JsonResponse({'errno': 0, 'msg': "收藏夹列表为空", 'data': favorite_list})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方法错误"})


@csrf_exempt
@validate_login
def get_favlist(request):
    if request.method == 'GET':
        favorite_id = request.GET.get('favorite_id')
        video_list = []
        try:
            Favorite.objects.get(id=favorite_id)
        except Favorite.DoesNotExist:
            return JsonResponse({'errno': 0, 'msg': "收藏夹不存在", 'data': video_list})

        if Favlist.objects.filter(favorite_id=favorite_id).exists():
            favlists = Favlist.objects.filter(favorite_id=favorite_id)
            for favlist in favlists:
                video = Video.objects.get(id=favlist.video_id)
                video_data = Video.to_simple_dict(video)
                video_list.append(video_data)
            return JsonResponse({'errno': 0, 'msg': "收藏列表查询成功", 'data': video_list})
        else:
            return JsonResponse({'errno': 0, 'msg': "收藏夹为空", 'data': video_list})

    else:
        return JsonResponse({'errno': 0, 'msg': "请求方法错误"})


@csrf_exempt
@validate_login
def delete_favorite(request):
    if request.method == 'POST':
        favorite_id = request.GET.get('favorite_id')
        try:
            favorite = Favorite.objects.get(id=favorite_id)
        except Favorite.DoesNotExist:
            return JsonResponse({'errno': 0, 'msg': "收藏夹不存在"})
        user_id = favorite.user_id
        if user_id != request.user.id:   # 最好是进别人的主页不显示删除按钮
            return JsonResponse({'errno': 0, 'msg': "没有操作权限"})

        if Favlist.objects.filter(favorite_id=favorite_id).exists():
            favlists = Favlist.objects.filter(favorite_id=favorite_id)
            for favlist in favlists:
                favlist.delete()
        favorite = Favorite.objects.get(id=favorite_id)
        favorite.delete()
        return JsonResponse({'errno': 0, 'msg': "收藏夹删除成功"})
    else:
        return JsonResponse({'errno': 0, 'msg': "请求方法错误"})
