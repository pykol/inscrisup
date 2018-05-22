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
