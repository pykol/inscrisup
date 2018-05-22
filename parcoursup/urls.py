# -*- coding: utf-8 -*-

# Inscrisup - Gestion des inscriptions administratives après Parcoursup
# Copyright (c) 2018 Florian Hatat
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^classe/(?P<slug>[-\w]+)/$', views.ClasseDetailView.as_view(), name='classe.details'),
    url(r'^etudiant/(?P<pk>[0-9]+)/$', views.EtudiantDetailView.as_view(), name='etudiant.details'),
    url(r'^etudiant/(?P<pk>[0-9]+)/demission$', views.etudiant_demission, name='etudiant.demission'),
    url(r'^proposition/ajout/$', views.proposition_ajout, name='proposition.ajout'),
    url(r'^action/$', views.ActionListView.as_view(), name='action.liste'),
    url(r'^action/(?P<pk>[0-9]+)/$', views.ActionDetailView.as_view(), name='action.details'),
    url(r'^action/(?P<pk>[0-9]+)/traiter$', views.action_traiter, name='action.traiter'),
]
