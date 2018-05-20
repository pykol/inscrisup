# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^classe/(?P<slug>[-\w]+)/$', views.classe, name='classe'),
]
