# -*- coding: utf-8 -*-

# Inscrisup - Gestion des inscriptions administratives après Parcoursup
# Copyright (c) 2018-2019 Florian Hatat
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

from django.urls import path, include

from . import views

rest_parcoursup_urlpatterns = [
	path('admissionCandidat', views.parcoursup.AdmissionView.as_view(), name='parcoursup_admission'),
	# Je pressens une blague de Parcoursup
	path('admissionCandidat/admissionCandidat', views.parcoursup.AdmissionView.as_view(), name='parcoursup_admission'),
]

urlpatterns = [
	path('', views.index, name='index'),
	path('classe/<slug:slug>/', views.ClasseDetailView.as_view(), name='classe.details'),
	path('classes/odf/', views.export_odf_classes, name='classes.odf'),
	path('internat/', views.internat_detail, name='internat.details'),
	path('etudiant/<int:pk>/', views.EtudiantDetailView.as_view(), name='etudiant.details'),
	path('etudiant/<int:pk>/pdf_adresse', views.export_pdf_adresse_etudiant, name='etudiant.pdf_adresse'),
	path('etudiant/<int:pk>/demission', views.etudiant_demission, name='etudiant.demission'),
	path('proposition/ajout/', views.proposition_ajout, name='proposition.ajout'),
	path('proposition/import/', views.parcoursup_import, name='proposition.parcoursup_import'),
	path('proposition/import/auto', views.parcoursup_auto_import, name='proposition.parcoursup_auto_import'),
	path('action/', views.ActionTodoListView.as_view(), name='action.liste'),
	path('action/<int:pk>/', views.ActionDetailView.as_view(), name='action.details'),
	path('action/<int:pk>/traiter', views.action_traiter, name='action.traiter'),
	path('action/pdf_adresses/', views.export_pdf_adresses, name='action.export_pdf_adresses'),
	path('action/pdf_adresses/etiquettes', views.export_etiquettes_adresses, name='action.export_pdf_etiquettes_adresses'),
	path('action/pdf_adresses/definitif', views.export_pdf_adresses_definitif, name='action.export_pdf_adresses_definitif'),

	path('parcoursup/', include(rest_parcoursup_urlpatterns)),
]
