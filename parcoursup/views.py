# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.views import generic
from django.urls import reverse

from .models import Classe, Etudiant, Action

def index(request):
    return render(request, 'parcoursup/index.html',
            {'classes_list': Classe.objects.all,})

class ClasseDetailView(generic.DetailView):
    model = Classe

class EtudiantDetailView(generic.DetailView):
    model = Etudiant

class ActionListView(generic.ListView):
    queryset = Action.objects.filter(statut = Action.STATUT_TODO)

class ActionDetailView(generic.DetailView):
    model = Action

def action_traiter(self, pk):
    action = get_object_or_404(Action, pk=pk)
    action.traiter(datetime.datetime.now())
    return HttpResponseRedirect(reverse('action.liste'))
