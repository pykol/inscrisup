# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.views import generic
from django.urls import reverse

from .models import Classe, Etudiant, Action
from .forms import PropositionForm

def index(request):
    return render(request, 'parcoursup/index.html',
            {'classes_list': Classe.objects.all,})

class ClasseDetailView(generic.DetailView):
    model = Classe

class EtudiantDetailView(generic.DetailView):
    model = Etudiant

def proposition_ajout(request):
    if request.method == 'POST':
        form = PropositionForm(request.POST)
        if form.is_valid():
            form.save()
            etudiant = Etudiant.objects.get(pk=form.data['etudiant'])
            return HttpResponseRedirect(etudiant.get_absolute_url())
    else:
        form = PropositionForm()
        try:
            # TODO existence de l'étudiant à vérifier ?
            form.fields['etudiant'].initial = request.GET['etudiant']
        except KeyError:
            pass

    return render(request, 'parcoursup/proposition_ajout.html',
            {
                'form': form,
            })

class ActionListView(generic.ListView):
    queryset = Action.objects.filter(statut = Action.STATUT_TODO)

class ActionDetailView(generic.DetailView):
    model = Action

def action_traiter(self, pk):
    action = get_object_or_404(Action, pk=pk)
    action.traiter(datetime.datetime.now())
    return HttpResponseRedirect(reverse('action.liste'))
