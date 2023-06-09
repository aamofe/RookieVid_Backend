import datetime
import json
import os
import pprint
import re
import shutil
import tempfile
import uuid
import PIL
import cv2
import numpy as np
import pytz
from django.utils import timezone
from qcloud_cos.cos_comm import CiDetectType
from qcloud_cos import CosServiceError
from decorator.decorator_permission import validate_login, validate_all
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q, Count, F, ExpressionWrapper
from django.db import models
from django.core import serializers
import datetime
from PIL import Image
from accounts.models import User, Follow
from notifications.views import send_sys_notification
from super_admin.models import Complain
from videos.cos_utils import get_cos_client, Category, Label, SubLabel
from videos.models import History, Video, Like, Comment, Reply, Favorite, Favlist
from random import sample
from django.contrib.auth.models import AnonymousUser
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# 视频分类标签
LABELS = ['娱乐', '军事', '生活', '音乐', '学习', '科技', '运动', '游戏', '影视', '美食']
@validate_all
def get_video_by_label(request):
    if request.method == 'GET':
        label = request.GET.get('label')
        num=request.GET.get('num')
        #print("num : ",num)
        if label not in LABELS:
            return JsonResponse({'errno': 1, 'msg': "标签错误！"})
        if not num:
            return JsonResponse({'errno': 1, 'msg': "视频数量错误！"})
        else:
            num=int(num)
        #print("num =",num)
        videos = Video.objects.filter(label=label,reviewed_status=1)
        if num==-1:
            num=videos.count()
            #print("num  : ",num)
        elif num<-1:
            return JsonResponse({'errno': 1, 'msg': "数量错误！"})
        else :
            num=min(num,videos.count())
        random_videos = sample(list(videos), num)
        video_list = []
        for video in random_videos:
            video_dict = video.to_dict()
            #print("video_url : ", video_dict.get('video_url'))
            video_list.append(video_dict)

        return JsonResponse({'errno': 0, 'msg': "返回成功！", 'video': video_list}, safe=False)
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@validate_all
def get_video_by_view_amount(request):
    if request.method=='GET':
        num=request.GET.get('num')
        label=request.GET.get('label')
        if len(num)==0 or not num.isdigit():
            return JsonResponse({'errno': 1, 'msg': "视频数量错误！"})
        else:
            num=int(num)
        if label not in LABELS:
            return JsonResponse({'errno': 1, 'msg': "标签错误！"})
        videos = Video.objects.filter(reviewed_status=1,label=label).order_by('-view_amount', 'id')
        videos = videos[:num]
        video_list=[]
        for v in videos:
            video_list.append(v.to_dict())
        return JsonResponse({'errno': 0, 'msg': "返回成功！", 'video': video_list}, safe=False)
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})    

@validate_all
def get_video_by_hotness(request):
    if request.method == 'GET':
        # 构建热度计算表达式
        num=request.GET.get('num')
        print("什么东西num : ",num)
        if not num or not num.isdigit():
            return JsonResponse({'errno': 1, 'msg': "视频数量错误！"})
        else:
            num=int(num)
        hotness_expression = ExpressionWrapper(
            Count('like_amount') + F('view_amount') * 0.5,
            output_field=models.FloatField()
        )
        # 获取符合条件的视频，并按热度计算排序
        videos = Video.objects.filter(reviewed_status=1).annotate(
            hotness_score=hotness_expression
        ).order_by('-hotness_score', '-like_amount', '-view_amount', 'id')
        # 获取前6个视频
        videos = videos[:(2*num)]
        videos = sample(list(videos),num)
        # print("数量 : ",)
        video_list = []
        for video in videos:
            video_dict = video.to_dict()
            #print("video_url: ", video_dict.get('video_url'))
            video_list.append(video_dict)

        return JsonResponse({'errno': 0, 'msg': "返回成功！", 'video': video_list}, safe=False)
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@validate_all
def get_related_video(request):
    if request.method == 'GET':
        video_id=request.GET.get('video_id')
        num=request.GET.get('num')
        if not video_id.isdigit():
            return JsonResponse({'errno': 1, 'msg': "视频ID错误！"})
        if not num or not num.isdigit():
            return JsonResponse({'errno': 1, 'msg': "视频数量错误！"})
        else:
            num=int(num)
        if num == 0:
            return JsonResponse({'errno': 1, 'msg': "参数不合法！"})
        try:
            video=Video.objects.get(id=video_id)
            videos=Video.objects.filter(reviewed_status=1)
            #提取视频的特征
            # 提取视频的特征
            features = [f"{video.title} {video.description} {video.label}" for video in videos]
            # 创建CountVectorizer对象，并将特征转换为特征向量
            vectorizer = CountVectorizer()
            feature_vectors = vectorizer.fit_transform(features)
            # 计算视频之间的相似度矩阵
            similarity_matrix = cosine_similarity(feature_vectors)
            # 获取目标视频的索引
            target_video_index = video.id
            # 获取相似视频的索引列表
            similar_videos_indices = np.argsort(similarity_matrix[target_video_index])[::-1]
            # 构建推荐视频列表
            recommendation_list = []
            for index in similar_videos_indices:
                if index != target_video_index:
                    try:
                        v=Video.objects.get(id=index)
                    except Video.DoesNotExist:
                        continue
                    recommendation_list.append(v.to_simple_dict())
                    if len(recommendation_list) == 2*num:
                        break
            random_videos = sample(list(recommendation_list), num)
            return JsonResponse({'errno': 0, 'msg': "返回成功！", 'video':random_videos}, safe=False)
        except Video.DoesNotExist:
            print("看来不错在 video_id : ",video_id)
            return JsonResponse({'errno': 1, 'msg': "视频不存在！"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})

def upload_video_method(video_file, video_id,):
    client, bucket_name, bucket_region = get_cos_client()
    if video_id == '' or video_id == 0:
        video_id = str(uuid.uuid4())
    file_name = video_file.name
    file_extension = file_name.split('.')[-1]  # 获取文件后缀
    print("ex :",file_extension)
    if file_extension !='mp4':
        return 1
    video_key = "video_file/{}".format(f'{video_id}.mp4')
    response_video = client.put_object(
        Bucket=bucket_name,
        Body=video_file,
        Key=video_key,
        StorageClass='STANDARD',
        ContentType="video/mp4"
    )
    #视频自动审核
    # video_key = "video_file/{}".format(f'{video_id}.mp4')
    # response_submit = client.ci_auditing_video_submit(
    #     Bucket=bucket_name,
    #     BizType='8f7d7f7e0393f74ee5de3394bc7bfeb1',
    #     Key=video_key,
    # )
    #pprint.pprint(response_submit)
    return 0
@validate_all
def test(request):
    cover_file = request.FILES.get('cover_file')
    cover_id = 3
    url = 'favorite_cover'
    res, cover_url,label=upload_cover_method(cover_file,cover_id,url)
    print('res = ',res)
    print('url =',url)
    print('label = ',label)
    return JsonResponse({'errno': 1, 'msg': label})

def upload_cover_method(cover_file, cover_id,url):
    client, bucket_name, bucket_region = get_cos_client()
    if cover_id == '' or cover_id == 0:
        cover_id = str(uuid.uuid4())
    file_name = cover_file.name
    file_extension = file_name.split('.')[-1]  # 获取文件后缀
    if file_extension =='jpg':
        ContentType = "image/jpg"
    elif file_extension =='jpeg':
        ContentType = "image/jpeg"
    elif file_extension =='png':
        ContentType = "image/png"
    else :
        return -2,None,None
    cover_key = f"{url}/{cover_id}.{file_extension}"
    response_cover = client.put_object(
        Bucket=bucket_name,
        Body=cover_file,
        Key=cover_key,
        StorageClass='STANDARD',
        ContentType=ContentType
    )
    if 'url' in response_cover :
        cover_url = response_cover['url']
    else:
        cover_url = f'https://{bucket_name}.cos.{bucket_region}.myqcloud.com/{cover_key}'
    response_submit = client.get_object_sensitive_content_recognition(
        Bucket=bucket_name,
        BizType='f90478ee0773ac0ab139c875ae167353',
        Key=cover_key,
        #DetectType=(CiDetectType.PORN | CiDetectType.ADS)
    )
    res = int(response_submit['Result'])
    Score=int(response_submit['Score'])
    #pprint.pprint(response_submit)
    if res == 1 or res==2 or Score>=60:
        category=response_submit['Category']
        label=response_submit['Label']
        subLabel=response_submit['SubLabel']
        if label=='Politics':
            #pprint.pprint(response_submit)

            content = "您的视频封面被判定为违规！" + \
                      "标签是" + Label[label] +  "，具体内容是：" + response_submit['PoliticsInfo']['Label'] + \
                      "。判定比例高达 " + str(Score) + "%。请修改"
        else:
            content = "您的视频封面被判定为违规！" +\
                  "标签是："+Label[label]+"，分类为："+Category[category]+"，具体内容是"+SubLabel[subLabel]+\
                  "。判定比例高达" + str(Score) + "%。请修改！"
        delete_cover_method(url,cover_id,file_extension)
        return 1,None,content
    return res,cover_url,None

def delete_cover_method(url,cover_id,file_extension):
    client, bucket_name, bucket_region = get_cos_client()
    cover_key = f"{url}/{cover_id}.{file_extension}"
    response = client.delete_object(
                Bucket=bucket_name,
                Key=cover_key
            )
def delete_video_method(video_id):
    client, bucket_name, bucket_region = get_cos_client()
    video_key = "video_file/{}".format(f'{video_id}.mp4')
    response = client.delete_object(
                Bucket=bucket_name,
                Key=video_key
            )
    pprint.pprint(response)

@csrf_exempt
@validate_login
def upload_video(request):
    if request.method == 'POST':
        # 获取上传的视频和封面文件
        user = request.user
        user_id =user.id
        label = request.POST.get('label')
        title = request.POST.get('title')
        description = request.POST.get('description')
        if not label:
            return JsonResponse({'errno': 1, 'msg': "标签不能为空！"})
        if not title :
            return JsonResponse({'errno':1, 'msg': "标题不能为空！"})
        if len(title)>45:
            return JsonResponse({'errno':1, 'msg': "标题必须少于45字！"})
        if not description:
            return JsonResponse({'errno': 1, 'msg': "描述不能为空！"})
        if label not in LABELS:
            return JsonResponse({'errno': 1, 'msg': "标签不合法！"})
        video_file = request.FILES.get('video_file')
        cover_file = request.FILES.get('cover_file')
        if not cover_file:
            return JsonResponse({'errno': 1, 'msg': "封面文件未上传"})
        if not video_file:
            return JsonResponse({'errno': 1, 'msg': "视频文件未上传"})
        # try:
        #     with tempfile.NamedTemporaryFile(delete=False) as temp_cover:
        #         temp_cover_path = temp_cover.name
        #         shutil.copyfileobj(cover_file, temp_cover)
        #     # 打开临时文件进行图像操作
        #     image = Image.open(temp_cover_path)
        #     width, height = image.size
        #     if (width != 1920 or height != 1080) and (width != 960 or height != 600):
        #         return JsonResponse({'errno': 1, 'msg': "封面图片尺寸必须为1920x1280或者960x600！当前尺寸为 %dx%d" % (width, height)})
        #     # 在完成操作后关闭图像文件
        #     image.close()
        #     # 删除临时文件
        #     os.remove(temp_cover_path)
        # except PIL.UnidentifiedImageError:
        #     return JsonResponse({'errno': 1, 'msg': "无法打开封面文件"})
        # with Image.open(cover_file) as img:
        #     img = img.convert('RGB')
        #     if img.width<img.height:#截取图片的中间部分，并等比扩大为1920×1080
                
        max_file_size = 300 * 1024 * 1024  # 300MB
        if video_file.size > max_file_size:
            return JsonResponse({'errno': 1, 'msg': "视频文件大小超过300MB限制"})
        video = Video.objects.create(
            label=label,
            title=title,
            description=description,
            user_id=user_id,
        )
        video_id = video.id
        cover_id=video_id
        res,cover_url,content=upload_cover_method(cover_file,cover_id,"cover_file")
        if res==-2:
            return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
        if res==1:
            video.delete()
            return JsonResponse({'errno': 1, 'msg': content})
        #上传视频
        res=upload_video_method(video_file,video_id)
        if res==1:
            return JsonResponse({'errno': 1, 'msg': "视频格式不合法"})
        
        video.cover_url = cover_url
        video.save()
        return JsonResponse({'errno': 0, 'msg': "封面审核通过！视频上传成功,待审核"})
    else:
        return JsonResponse({'errno':1, 'msg': "请求方法错误！"})

def call_back(request):
    if request.method=='POST':
        body = json.loads(request.body)
        code = body.get("code")#错误码，值为0时表示审核成功，非0表示审核失败
        data = body.get("data")#视频审核结果的详细信息。
        JobId = data.get("trace_id")
        url = data.get("url")
        result = int(data.get("result"))

        porn_info = data.get("porn_info")#审核场景为涉黄的审核结果信息。
        ads_info=data.get("ads_info")
        terrorist_info=data.get("terrorist_info")
        politics_info=data.get("'politics_info")

        if ads_info.get("hit_flag")!=0:
            score=ads_info.get("score")
            content = "您的视频被判定为违规！" + "标签是:广告元素，" +"判定比例高达 " + str(score) + "%，"
        elif porn_info.get("hit_flag")!=0:
            score=porn_info.get("score")
            content = "您的视频被判定为违规！" + "标签是:涉黄元素，" +"判定比例高达 " + str(score) + "%，"
        elif politics_info.get("hit_flag")!=0:
            score=politics_info.get("score")
            content = "您的视频被判定为违规！" + "标签是:政治元素，" +"判定比例高达 " + str(score) + "%，"
        elif terrorist_info.get("hit_flag")!=0:
            score=terrorist_info.get("score")
            content = "您的视频被判定为违规！" + "标签是:暴力元素，" +"判定比例高达 " + str(score) + "%，"
        print(content)

        video_id=re.search(r'\d+(?=\.\w+$)', url).group()
        if not Video.objects.filter(id=video_id).exists():
            return JsonResponse({'errno': 1, 'result':result})
        video=Video.objects.get(id=video_id)
        user=User.objects.get(id=video.user_id)
        file_extension = video.cover_url.split('.')[-1]  # 获取文件后缀

        if result == 0 :#审核正常
            video.reviewed_status=1#审核通过
            video.video_url = url
            video.reviewed_at=timezone.now()
            video.save()
            #给up主发信息
            title = "视频发布成功！"
            content = "亲爱的" + user.username + '你好呀!\n' '视频审核通过啦，快和小伙伴分享分享你的视频叭~'
            #create_message(user_id, title, content)
            send_sys_notification(0,video.user_id,title,content,0,0)
            #给所有粉丝发信息
            fan_list=Follow.objects.filter(following_id=user.id)
            for fan in fan_list:
                fan_id=fan.follower_id
                title = "你关注的博主发布新视频啦！"
                fan=User.objects.get(id=fan_id)
                content = "亲爱的" + fan.username + '你好呀!\n''你关注的博主发布新视频啦！快去看看，然后在评论区留下自己的感受叭~'
                send_sys_notification(video.user_id,fan.id,title,content,0,0)
        elif result==1:
            video.delete()
            delete_cover_method(video.id,file_extension)
            delete_video_method(video.id)
            title = "视频审核失败！"
            content = "亲爱的" + user.username + ' 你好呀!\n'+ content + '\n下次不要再上传这类的视频了哟，这次就算了嘿嘿~'
            send_sys_notification(0,video.user_id,title,content,0,0)
            #给up主发信息
        elif result==2:
            #给up主发信息
            title = "视频需要人工审核！"
            video.video_url = url
            video.save()
            content = "亲爱的" + user.username + ' 你好呀!\n' + content + '\n我们需要人工再进行审核，不要着急哦~'
            send_sys_notification(0,video.user_id,title,content,0,0)
        return JsonResponse({'errno': 1, 'result':result})
@validate_login
def delete_video(request):
    if request.method == 'POST':
        # 获取操作类型和视频ID
        user=request.user
        video_id = request.POST.get('video_id')
        try:
            # 根据视频ID从数据库中删除该视频记录
            video = Video.objects.get(id=video_id)
            file_extension = video.cover_url.split('.')[-1]  # 获取文件后缀
            if not (user.id==video.user_id or user.status==1):
                return JsonResponse({'errno': 1, 'msg': '没有权限删除'})
            video.delete()
            delete_cover_method("cover_file",video.id,file_extension)
            delete_video_method(video.id)
            return JsonResponse({'errno': 0, 'msg': '删除成功'})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': '视频不存在'})
    else:
        return JsonResponse({'errno': 1, 'msg': '请求方法不合法'})

@validate_login   
def update_video(request):
    if request.method == 'POST':
        user=request.user
        video_id = request.POST.get('video_id')
        label = request.POST.get('label')
        title = request.POST.get('title')
        description = request.POST.get('description')
        try:
            video = Video.objects.get(id=video_id)
            if user.id !=video.user_id:
                return JsonResponse({'errno':1, 'msg': '没有权限更新'})
            cnt=0
            if title:
                video.title = title
                cnt+=1
            if label and label!=video.label:
                if label in LABELS :
                    video.label = label
                    cnt+=1
                else:
                    return JsonResponse({'errno': 1, 'msg': '标签不合法'})
            if  description and description!=video.description:
                video.description = description
                cnt+=1
            if cnt==0:
                return JsonResponse({'errno': 1, 'msg': '没有更新'})
            video.save()
            return JsonResponse({'errno': 0, 'msg': '更新成功'})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': '视频不存在'})
    else:
        return JsonResponse({'errno': 1, 'msg': '请求方法不合法'})
    
@validate_login
def get_video(request):
    if request.method == 'GET':
        user=request.user
        print('hhhh ',user.id)
        videos0 = Video.objects.filter(user_id=user.id, reviewed_status=0)
        video_list0 = []
        videos1 = Video.objects.filter(user_id=user.id, reviewed_status=1)
        video_list1 = []
        for v in videos0:
            video_list0.append(v.to_simple_dict())
        for v in videos1:
            video_list1.append(v.to_simple_dict())
        return JsonResponse({'errno': 0, 'video0': video_list0, 'video1': video_list1, 'msg': '获取稿件成功'})
        # except Video.DoesNotExist:
        #     return JsonResponse({'errno': 1, 'msg': '没有上传稿件'})
    else:
        return JsonResponse({'errno': 1, 'msg': '请求方法不合法'})
@validate_login
def get_one_video(request):
    if request.method == 'GET':
        user=request.user
        video_id=request.GET.get('video_id')
        if not video_id:
            return JsonResponse({'errno': 1, 'msg': '请传入视频ID！'})
        try :
            video=Video.objects.get(id=video_id)
            if video.user_id!=user.id:
                return JsonResponse({'errno': 1, 'msg': '该视频不属于您！'})
            return JsonResponse({'errno': 0, 'video':video.to_simple_dict() , 'msg': '获取稿件成功'})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1,  'msg': '稿件不存在'})
    else:
        return JsonResponse({'errno': 1, 'msg': '请求方法不合法'})
@validate_all
def search(request):
    if request.method == 'GET':
        keyword = request.GET.get('keyword')
        if not keyword:
            return JsonResponse({'errno': 1, 'msg': '关键字不能为空'})
        # 使用 Q 对象进行模糊查询
        query_video = Q(title__icontains=keyword) | Q(description__icontains=keyword)
        videos = Video.objects.filter(query_video)
        query_user = Q(username__icontains=keyword) | Q(signature__icontains=keyword)|Q(uid__icontains=keyword)
        users=User.objects.filter(query_user)
        video_list = []
        user_list=[]
        for v in videos:
            video_list.append(v.to_simple_dict())
        for u in users:
            user=request.user
            uu=u.to_dict()
            if isinstance(user, AnonymousUser):
                followed=0
            else:
                try:
                    follow=Follow.objects.get(follower_id=user.id,following_id=u.id)
                    followed=1
                except Follow.DoesNotExist:
                    followed=0
            uu['followed']=followed
            user_list.append(uu)
        return JsonResponse({'errno': 0, 'msg': "返回成功！", 'video': video_list,'user':user_list}, safe=False)
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})



@validate_all
def view_video(request):
    if request.method == 'GET':
        video_id = request.GET.get('video_id')
        if not video_id.isdigit():
            return JsonResponse({'errno': 1, 'msg': '视频id不合法！'})
        try:
            video = Video.objects.get(id=video_id)
            # 将字典列表作为JSON响应返回
            video.view_amount += 1
            video.save()
            v=video.to_dict()
            user = request.user
            user_id=user.id
            if isinstance(user, AnonymousUser):
                liked=0
                favorited = 0
                followed=0
            else:
                try :
                    like=Like.objects.get(video_id=video_id,user_id=user_id)
                    liked=1
                except Like.DoesNotExist:
                    liked=0
                favorites=Favlist.objects.filter(video_id=video_id,user_id=user_id)
                if favorites.count()!=0:
                    favorited=1
                else:
                    favorited=0
                try:
                    follow=Follow.objects.get(follower_id=user.id,following_id=video.user_id)
                    followed=1
                except Follow.DoesNotExist:
                    followed=0
                try:
                    history=History.objects.get(user_id=user_id,video_id=video_id)
                    history.created_at=timezone.now()
                    history.save()
                except History.DoesNotExist:
                    history=History.objects.create(
                    user_id=user_id,
                    video_id=video_id,
                    created_at=timezone.now()
                    )
            v['liked']=liked
            v['favorited']=favorited
            v['followed']=followed
            total_comment_amount=0
            comment_amount=0
            comments = Comment.objects.filter(video_id=video_id,comment_id=0)
            comment_list = []
            for c in comments:
                cc=c.to_dict()
                reply=Comment.objects.filter(video_id=video_id,comment_id=c.id)
                for r in reply:
                    cc['reply'].append(r.to_dict())
                comment_list.append(cc)
                total_comment_amount+=reply.count()+1
                cc['reply_amount']=reply.count()
                comment_amount+=1
                #print('id: ',cc.get('id'))

            v['total_comment_amount'] =total_comment_amount
            v['comment_amount'] =comment_amount
            
            return JsonResponse({'errno': 0, 'msg': "返回成功！", 'video': v, 'comment': comment_list},safe=False)
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': '视频不存在'})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@validate_all
def get_comment(request):
    if request.method == 'GET':
        video_id = request.GET.get('video_id')
        try:
            video = Video.objects.get(id=video_id)
            comments = Comment.objects.filter(video_id=video_id, comment_id=0).order_by('-created_at')
            comment_list = []
            total_comment_amount = 0
            comment_amount = 0
            amount = {}
            for c in comments:
                cc = c.to_dict()
                reply = Comment.objects.filter(video_id=video_id, comment_id=c.id)
                for r in reply:
                    cc['reply'].append(r.to_dict())
                comment_amount += 1
                total_comment_amount += reply.count() + 1
                cc['reply_amount'] = reply.count()
                comment_list.append(cc)
            amount['total_comment_amount'] = total_comment_amount
            amount['comment_amount'] = comment_amount
            return JsonResponse({'errno': 0, 'msg': "返回成功！", 'comment': comment_list, 'amount': amount}, safe=False)
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': '视频不存在'})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@csrf_exempt
@validate_login
def comment_video(request):
    if request.method == 'POST':
        user = request.user
        user_id=user.id
        video_id = request.POST.get('video_id')
        content = request.POST.get('content')
        try:
            video = Video.objects.get(id=video_id)
            if len(content) == 0:
                return JsonResponse({'errno': 1, 'msg': '评论不能为空'})
            comment = Comment.objects.create(
                user_id=user_id,
                content=content,
                video_id=video_id,
                comment_id=0,
            )
            u=User.objects.get(id=video.user_id)
            comment.save()
            title = "有人给你点赞啦"
            content = "亲爱的" + u.username + ' 你好呀!\n有人给你点赞啦，快去看看吧'
            send_sys_notification(user_id, u.id , title, content, 0, 0)
            return JsonResponse({'errno': 0, 'msg': '评论成功'})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': '视频不存在'})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@validate_login
def delete_comment(request):
    if request.method=='POST':
        user=request.user
        comment_id=request.POST.get('comment_id')
        try:
            comment=Comment.objects.get(id=comment_id,comment_id=0)
            try:
                #video=Video.objects.get(id=comment.video_id)
                video = Video.objects.get(id=comment.video_id)
                if not (user.id == comment.user_id or user.id == video.user_id or user.status == 1):
                    return JsonResponse({'errno': 1, 'msg': "没有权限删除评论！"})
                reply = Reply.objects.filter(comment_id=comment_id)
                for r in reply:
                    r.delete()
                comment.delete()
                return JsonResponse({'errno': 0, 'msg': "删除评论成功！"})
            except:
                return JsonResponse({'errno': 1, 'msg': "视频不存在！"})
        except Comment.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "评论不存在！"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@csrf_exempt
@validate_login
def reply_comment(request):
    if request.method == 'POST':
        # 获取请求中传入的参数
        user = request.user
        user_id = user.id
        comment_id = request.POST.get('comment_id')
        content = request.POST.get('content')
        video_id=request.POST.get('video_id')
        try:
            comment=Comment.objects.get(id=comment_id)
            try:
                video = Video.objects.get(id=video_id)
                if len(content) == 0:
                    return JsonResponse({'errno': 1, 'msg': '回复不能为空'})
                c = Comment(user_id=user_id,
                            comment_id=comment_id,
                            content=content,
                            video_id=video_id,
                            created_at=timezone.now()
                )
                c.save()
                u=User.objects.get(id=comment.user_id)
                title = "有人给你回复啦"
                content = "亲爱的" + u.username + ' 你好呀!\n有人给你的评论回复啦，快去看看吧'
                send_sys_notification(user_id, u.id, title, content, 0, 0)
                return JsonResponse({'errno': 0, 'errmsg': '回复成功'})
            except Video.DoesNotExist:
                return JsonResponse({'errno': 1, 'msg': '视频不存在'})
        except Comment.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': '评论不存在'})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@validate_login
def delete_reply(request):
    if request.method=='POST':
        user=request.user
        reply_id=request.POST.get('reply_id')
        try:
            c=Comment.objects.get(id=reply_id)
            try:
                comment = Comment.objects.get(id=c.comment_id)
                try:
                    video = Video.objects.get(id=c.video_id)
                    if not (user.id == comment.user_id or user.id == c.user_id or user.id == video.user_id or user.status == 1):
                        return JsonResponse({'errno': 1, 'msg': "没有权限删除回复！"})
                    c.delete()
                    return JsonResponse({'errno': 0, 'msg': "删除回复成功！"})
                except:
                    return JsonResponse({'errno': 1, 'msg': "视频不存在！"})
            except:
                return JsonResponse({'errno': 1, 'msg': "评论不存在！"})
        except Comment.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "回复不存在！"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})

@csrf_exempt
@validate_login
def like_video(request):
    if request.method == 'POST':
        # 获取请求中传入的参数
        user = request.user
        user_id = user.id
        video_id = request.POST.get('video_id')
        #print('hahha',user.id)
        try:
            video=Video.objects.get(id=video_id)
            # 检查该用户是否已经点赞过该视频
            try:
                like = Like.objects.get(user_id=user_id, video_id=video_id)
                # 用户已经点赞过该视频，则取消点赞
                like.delete()
                video.like_amount -= 1
                if video.like_amount < 0:
                    video.like_amount = 0
                video.save()
                # print('video.like_amount : ',video.like_amount)
                return JsonResponse({'errno': 0, 'msg': "点赞取消成功！"})
            except Like.DoesNotExist:
                # 用户没有点赞过该视频，则添加点赞记录
                like = Like(user_id=user_id, video_id=video_id)
                like.save()
                u = User.objects.get(id=video.user_id)
                title = "有人给你的视频点赞啦"
                content = "亲爱的" + u.username + ' 你好呀!\n有人给你的视频点赞啦，快去看看吧'
                send_sys_notification(user_id, u.id, title, content, 0, 0)
                video.like_amount += 1
                video.save()
                # ('video.like_amount : ',video.like_amount)
                return JsonResponse({'errno': 0, 'msg': "点赞成功！"})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "视频不存在！"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@validate_login
def create_favorite(request):
    if request.method == 'POST':
        # 获取请求中传入的参数
        user = request.user
        user_id=user.id
        #print('hah',user_id)
        title = request.POST.get('title')
        description= request.POST.get('description')
        if not description:
            #print(111222)
            description = ""
        is_private= request.POST.get('is_private')
        #print('provate : ',is_private)
        if not is_private or not is_private.isdigit() :
            is_private = 0
        is_private=int(is_private)
        if is_private!=0 and is_private!=1:
            is_private=0
        if not title:
            title="默认收藏夹"
        #favorite_cover=request.FILES.get("favorite_cover")
        # if len(status)==0 or not status.isdigit():
        #     return JsonResponse({'errno': 1, 'msg': "收藏夹状态错误！"})
        # else:
        #     status=int(status)
        # if len(description)==0 or not (status == 0 or status == 1):
        #     return JsonResponse({'errno': 1, 'msg': "参数不合法！"})
        try:
            favorite=Favorite.objects.get(user_id=user_id,title=title)
            return JsonResponse({'errno': 1, 'msg': "收藏夹已存在！"})
        except Favorite.DoesNotExist:
            #print('provate : ',is_private)
            favorite=Favorite(title=title,
                              description=description,
                              is_private=is_private,
                              user_id=user_id,
                              created_at=timezone.now()
                              )
            favorite.save()
            #print("创建好了 private : ",is_private)
            # if favorite_cover:
            #     res, cover_url, label = upload_cover_method(favorite_cover,favorite.id, "favorite_cover")
            #     if res == -2:
            #         return JsonResponse({'errno': 1, 'msg': "封面图片格式不合法"})
            #     if res == 1:
            #         favorite.delete()
            #         return JsonResponse({'errno': 1, 'msg': "上传失败！图片含有违规内容 ：" + label})
            #     favorite.cover_url=cover_url
            #     favorite.save()
            return JsonResponse({'errno': 0, 'msg': "创建收藏夹成功！"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
@validate_login
def get_favorite(request):#判断是否已收藏
    if request.method == 'GET':
        user=request.user
        user_id=user.id
        video_id=request.GET.get('video_id')
        try :
            video=Video.objects.get(id=video_id)
            favorite_list = []
            try:
                favorite = Favorite.objects.filter(user_id=user_id)
                for f in favorite:
                    ff = f.to_dict()
                    try:
                        favlist = Favlist.objects.get(video_id=video_id, favorite_id=f.id)
                        ff['favorited'] = 1
                    except Favlist.DoesNotExist:
                        ff['favorited'] = 0
                    favorite_list.append(ff)
                return JsonResponse({'errno': 0, 'favorite':favorite_list,'msg': "获取收藏夹成功！"})
            except Favorite.DoesNotExist:
                return JsonResponse({'errno': 1, 'msg': "无收藏夹，请创建收藏夹！"})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "视频不存在，请重新传入！"})
    else:
         return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})

@validate_login
def favorite_video(request):
    if request.method == 'POST':
        user = request.user
        user_id = user.id
        video_id=request.POST.get('video_id')
        favorite_list=request.POST.getlist('favorite_list',[])
        id_list=[]
        try:
            video=Video.objects.get(id=video_id)
            s=favorite_list[0]
            if ',' in s:
                id_list=list(map(int,s.split(',')))
            elif len(s)!=0:
                id_list.append(int(s))
                print('ssss : ',id_list[0])
            else :
                id_list=[]
            for f_id in id_list : #添加收藏
                # print('f_id : ',f_id)
                # print("type : ",type(f_id))
                if not f_id :
                    print("haha")
                    continue
                try:
                    favorite=Favorite.objects.get(id=f_id,user_id=user_id)
                except:
                    return JsonResponse({'errno': 1, 'msg': "收藏夹不属于用户！"})
                try :
                    favlist=Favlist.objects.get(favorite_id=f_id,video_id=video_id)
                except Favlist.DoesNotExist:#如果没收藏过这个视频，那就判断这个收藏夹有多少视频，如果为1
                    #print("应该收藏的f_id :",f_id)
                    favlist=Favlist.objects.create(
                        user_id=user_id,
                        favorite_id=f_id,
                        video_id=video_id,
                        created_at=timezone.now()
                    )
                    #print('收藏具体列表的 id : ',favlist.id)
                    favorite_video_list=Favlist.objects.filter(favorite_id=f_id)
                    if favorite_video_list.count()==1:
                        favorite.cover_url=video.cover_url
                        favorite.save()
            favorites=Favorite.objects.filter(user_id=user_id)
            for f in favorites:#用户所有的收藏夹
                if f.id not in id_list :#没被选中
                    #pprint.pprint(id_list)
                    try:
                        favlist = Favlist.objects.get(favorite_id=f.id,video_id=video.id)
                        favlist.delete()
                        #查找该收藏夹还有多少个视频
                        favorite_video_list=Favlist.objects.filter(favorite_id=f.id).order_by('created_at')
                        cover_url=''#更新收藏夹的封面
                        while(favorite_video_list.count()>1):
                            v_id=favorite_video_list.first().video_id
                            try :
                                v=Video.objects.get(id=v_id)
                                cover_url=v.cover_url
                                break
                            except Video.DoesNotExist:
                                favorite_video_list.first().delete()
                        if favorite_video_list.count()==0:
                            cover_url='https://aamofe-1315620690.cos.ap-beijing.myqcloud.com/favorite_cover/0.png'
                            f.cover_url=cover_url
                            f.save()
                    except Favlist.DoesNotExist:
                        continue
            return JsonResponse({'errno': 0, 'msg': "收藏成功！"})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "视频不存在！"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})

shanghai_tz = pytz.timezone('Asia/Shanghai')
@validate_login
def is_complaint(request):
    if request.method=='GET':
        user=request.user
        video_id=request.GET.get('video_id')
        if not video_id:
            return JsonResponse({'errno': 1, 'is_complaint': 0, 'msg': "请传入视频ID！"})
        created_at =timezone.now()
        try:
            video=Video.objects.get(id=video_id)
            complains = Complain.objects.filter(video_id=video_id, user_id=user.id).order_by('created_at')
            if complains.exists():
                complain = complains.last()

                content = '上一次投诉时间:' + (complain.created_at+datetime.timedelta(hours=8)).strftime(
                    '%Y-%m-%d %H:%M:%S') + ' 现在时间: ' + (created_at+datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                # print('user_id ',user.id,"video_id :",video.id)
                # print("hah",content)
                if(created_at-complain.created_at).total_seconds() < 3600:
                    return JsonResponse({'errno': 0, 'is_complaint': 1, 'msg': "投诉间隔小于1小时！" + content})
                else:
                    return JsonResponse({'errno': 0, 'is_complaint': 0, 'msg': "可以投诉！"})
            else :
                print("不存在 啊 ")
                return JsonResponse({'errno': 0,'is_complaint':0, 'msg': "可以投诉！"})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 0, 'is_complaint': 1, 'msg': "视频不存在，不可以投诉！"})
@validate_login
def complain_video(request):
    if request.method=='POST':
        user=request.user
        video_id=request.POST.get('video_id')
        content=request.POST.get('content')
        try :
            video=Video.objects.get(id=video_id)
            if len(content)==0:
                return JsonResponse({'errno': 1, 'msg': "投诉原因不能为空！"})
            complain = Complain(video_id=video_id, user_id=user.id, reason=content,status=0)
            complain.save()
            complain_time = complain.created_at
            complain_timezone = complain_time.tzinfo
            print('投诉时间:', complain_time)
            print('投诉时间的时区:', complain_timezone)
            return JsonResponse({'errno': 0, 'msg': "投诉成功！"})
        except Video.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "视频不存在！"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})

@validate_login
def get_data(request):
    if request.method=='GET':
        user=request.user
        print("user_id : ",user.id)
        #评论数 粉丝 播放量 点赞 收藏 投稿的视频总数
        amount={}
        total_comment_amount=0
        follower_amount=0
        total_view_amount=0
        total_like_amount=0
        total_favorite_amount=0
        video_amount=0
        videos=Video.objects.filter(user_id=user.id)
        
        print('len :' ,videos.count())
        if videos.exists():
            video_amount=videos.count()
            for video in videos:
                comments=Comment.objects.filter(video_id=video.id)
                total_comment_amount+=comments.count()
                total_view_amount+=video.view_amount
                total_like_amount+=video.like_amount
                favlist=Favlist.objects.filter(video_id=video.id)
                total_favorite_amount+=favlist.count()
        followers=Follow.objects.filter(following_id=user.id)
        follower_amount=followers.count()
        amount['follower_amount']=follower_amount
        amount['total_comment_amount'] =total_comment_amount
        amount['total_view_amount'] =total_view_amount
        amount['total_like_amount'] =total_like_amount
        amount['total_favorite_amount'] =total_favorite_amount
        amount['video_amount'] =video_amount
        return JsonResponse({'errno':0,'amount':amount})
    else:
        return JsonResponse({'errno':1,'amount':'请求方法错误'})

@validate_login
def get_history(request):
    if request.method=='GET':
        user=request.user
        histories=History.objects.filter(user_id=user.id).order_by("-created_at")
        history_list=[]
        for h in histories:
            history_list.append(h.to_dict())
        return JsonResponse({'errno':0,'history':history_list,'msg':"返回成功"})
    else:
        return JsonResponse({'errno':1,'msg':'请求方法错误'})


