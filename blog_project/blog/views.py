# -*- coding: utf-8 -*-
import logging
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.db.models import Count
from .models import *
from .forms import *

logger = logging.getLogger('blog.views')


# Create your views here.
def global_setting(request):
    # 站点基本信息
    site_url = settings.SITE_URL
    site_name = settings.SITE_NAME
    site_desc = settings.SITE_DESC
    # 作者社交网站信息
    weibo_sina = settings.WEIBO_SINA
    weibo_tencent = settings.WEIBO_TENCENT
    pro_rss = settings.PRO_RSS
    pro_email = settings.PRO_EMAIL
    # 分类信息获取（导航数据）
    category_list = Category.objects.all()[:6]
    # 文章归档数据
    archive_list = Article.objects.distinct_date()
    # 广告数据
    ad_list = Ad.objects.all()
    ad_list_ = [[ad.index, ad.title, ad.description] for ad in ad_list]
    # 标签云数据
    tag_list = Tag.objects.all()
    # 友情链接数据
    link_list = Links.objects.all()
    # 浏览排行
    article_click_list = Article.objects.order_by("-click_count")[:6]
    # 站长推荐
    article_recommend_list = Article.objects.order_by("-click_count").filter(is_recommend=1)[:6]
    # 评论排行
    comment_count_list = Comment.objects.values('article').annotate(comment_count=Count('article')).order_by(
        '-comment_count')
    article_comment_list = [Article.objects.get(pk=comment['article']) for comment in comment_count_list]
    return locals()


def index(request):
    try:
        # 最新文章数据
        article_list = Article.objects.all()
        article_list = getPage(request, article_list)
        title = "首页"
        # 文章归档
        # 1、先要去获取到文章中有的 年份-月份  2015/06文章归档
        # 使用values和distinct去掉重复数据（不可行）
        # print Article.objects.values('date_publish').distinct()
        # 直接执行原生sql呢？
        # 第一种方式（不可行）
        # archive_list = Article.objects.raw(
        #     'SELECT id, DATE_FORMAT(date_publish, "%%Y-%%m") as col_date FROM blog_article ORDER BY date_publish')
        # for archive in archive_list:
        #     print archive
        # 第二种方式（不推荐）
        # cursor = connection.cursor()
        # cursor.execute(
        # "SELECT DISTINCT DATE_FORMAT(date_publish, '%Y-%m') as col_date FROM blog_article ORDER BY date_publish")
        # row = cursor.fetchall()
        # print row
    except Exception as e:
        # print(e)
        logger.error(e)
    return render(request, 'index.html', locals())


def archive(request):
    try:
        title = "文章归档"
        # 先获取客户端提交的信息
        year = request.GET.get('year', None)
        month = request.GET.get('month', None)
        article_list = Article.objects.filter(date_publish__icontains=year + '-' + month)
        article_list = getPage(request, article_list)
    except Exception as e:
        logger.error(e)
        pass
    return render(request, 'archive.html', locals())


# 按标签查询对应的文章列表
def tag(request):
    try:
        tag_id = request.GET.get('id', None)
        tag = Tag.objects.get(pk=tag_id)
        title = tag.name
        article_list = tag.article_set.all()
        # article_list = Article.objects.filter(tag__id=tag_id)
        article_list = getPage(request, article_list)
    except Exception as e:
        # print(e)
        logger.error(e)
    return render(request, 'archive.html', locals())


# 分页代码
def getPage(request, article_list):
    paginator = Paginator(article_list, 5)
    try:
        page = int(request.GET.get('page', 1))
        article_list = paginator.page(page)
    except (EmptyPage, InvalidPage, PageNotAnInteger):
        article_list = paginator.page(1)
    return article_list


# 文章详情
def article(request):
    try:
        title = "文章详情"
        # 获取文章id
        id = request.GET.get('id', None)
        try:
            # 获取文章信息
            article = Article.objects.get(pk=id)
        except Article.DoesNotExist:
            return render(request, 'failure.html', {'reason': '没有找到对应的文章'})

        # 评论表单
        comment_form = CommentForm({'author': request.user.username,
                                    'email': request.user.email,
                                    'url': request.user.url,
                                    'article': id} if request.user.is_authenticated() else {'article': id})
        # 获取评论信息
        comments = Comment.objects.filter(article=article).order_by('id')
        comment_list, comment_count = [], 0
        for comment in comments:
            for item in comment_list:
                if not hasattr(item, 'children_comment'):
                    setattr(item, 'children_comment', [])
                if comment.pid == item:
                    item.children_comment.append(comment)
                    comment_count += 1
                    break
            if comment.pid is None:
                comment_list.append(comment)
                comment_count += 1
    except Exception as e:
        # print(e)
        logger.error(e)
    return render(request, 'article.html', locals())


# 提交评论
def comment_post(request):
    try:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            # 获取表单信息
            comment = Comment.objects.create(username=comment_form.clean_author(),
                                             email=comment_form.clean_email(),
                                             url=comment_form.cleaned_data["url"],
                                             content=comment_form.cleaned_data["comment"],
                                             article_id=comment_form.cleaned_data["article"],
                                             user=request.user if request.user.is_authenticated() else None)
            comment.save()
        else:
            return render(request, 'failure.html', {'reason': comment_form.errors})
    except Exception as e:
        print(e)
        logger.error(e)
    return redirect(request.META['HTTP_REFERER'])


# 注销
def do_logout(request):
    try:
        logout(request)
    except Exception as e:
        # print(e)
        logger.error(e)
    return redirect(request.META['HTTP_REFERER'])


# 注册
def do_reg(request):
    try:
        title = "注册"
        if request.method == 'POST':
            reg_form = RegForm(request.POST)
            if reg_form.is_valid():
                # 注册
                user = User.objects.create(username=reg_form.cleaned_data["username"],
                                           email=reg_form.clean_email(),
                                           url=reg_form.cleaned_data["url"],
                                           password=make_password(reg_form.cleaned_data["password"]), )
                user.save()

                # 登录
                user.backend = 'django.contrib.auth.backends.ModelBackend'  # 指定默认的登录验证方式
                login(request, user)
                return redirect(request.POST.get('source_url'))
            else:
                return render(request, 'failure.html', {'reason': reg_form.errors})
        else:
            reg_form = RegForm()
    except Exception as e:
        # print(e)
        logger.error(e)
    return render(request, 'reg.html', locals())


# 登录
def do_login(request):
    try:
        title = "登录"
        if request.method == 'POST':
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                # 登录
                username = login_form.cleaned_data["username"]
                password = login_form.cleaned_data["password"]
                user = authenticate(username=username, password=password)
                if user is not None:
                    user.backend = 'django.contrib.auth.backends.ModelBackend'  # 指定默认的登录验证方式
                    login(request, user)
                else:
                    return render(request, 'failure.html', {'reason': '登录验证失败'})
                return redirect(request.POST.get('source_url'))
            else:
                return render(request, 'failure.html', {'reason': login_form.errors})
        else:
            login_form = LoginForm()
    except Exception as e:
        # print(e)
        logger.error(e)
    return render(request, 'login.html', locals())


def category(request):
    try:
        # 先获取客户端提交的信息
        cid = request.GET.get('cid', None)
        try:
            category = Category.objects.get(pk=cid)
            title = category.name
        except Category.DoesNotExist:
            return render(request, 'failure.html', {'reason': '分类不存在'})
        article_list = Article.objects.filter(category=category)
        article_list = getPage(request, article_list)
    except Exception as e:
        # print(e)
        logger.error(e)
    return render(request, 'category.html', locals())
