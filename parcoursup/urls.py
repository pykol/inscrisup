# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^classe/(?P<slug>[-\w]+)/$', views.ClasseDetailView.as_view(), name='classe.details'),
    url(r'^etudiant/(?P<pk>[0-9]+)/$', views.EtudiantDetailView.as_view(), name='etudiant.details'),
    url(r'^proposition/ajout/$', views.proposition_ajout, name='proposition.ajout'),
    url(r'^action/$', views.ActionListView.as_view(), name='action.liste'),
    url(r'^action/(?P<pk>[0-9]+)/$', views.ActionDetailView.as_view(), name='action.details'),
    url(r'^action/(?P<pk>[0-9]+)/traiter$', views.action_traiter, name='action.traiter'),
]
