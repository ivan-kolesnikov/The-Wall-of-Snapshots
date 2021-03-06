"""twos_rest URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from twos_rest_api import views
from django.urls import path, re_path
#from django.conf.urls import url

urlpatterns = [
    path('admin/', admin.site.urls),
    # all channels + select channel by channel id
    path('channels/', views.ChannelsList.as_view()),
    re_path('channels/(?P<pk>[0-9]+)/$', views.ChannelDetail.as_view()),
    # update channels
    path('channels/update/', views.ChannelsUpdate.as_view()),
    # channels errors + select channel errors by channel id
    path('channels/errors/', views.ErrorsList.as_view()),
    re_path('channels/(?P<pk>[0-9]+)/errors/', views.ErrorDetail.as_view()),
    # channels down statistic
    path('channels/down/', views.ChannelDownList.as_view()),
    path('channels/down/now', views.ChannelDownNowList.as_view()),

    path('bitrate/', views.BitrateList.as_view()),



    path('channels/events/', views.ChannelEventList.as_view()),
    re_path('channels/(?P<pk>[0-9]+)/events', views.ChannelEventDetail.as_view()),
    path('events/', views.EventsList.as_view()),
    path('guards/config/', views.GuardConfigList.as_view()),
    re_path('guards/(?P<pk>[0-9]+)/config/', views.GuardConfigDetail.as_view()),
]
