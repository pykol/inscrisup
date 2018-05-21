# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views import generic

from .models import Classe, Etudiant

def index(request):
    return render(request, 'parcoursup/index.html',
            {'classes_list': Classe.objects.all,})

class ClasseDetailView(generic.DetailView):
    model = Classe

class EtudiantDetailView(generic.DetailView):
    model = Etudiant
