# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from .models import Classe

def index(request):
    return HttpResponse("Inscrisup")

def classe(request, slug):
    classe = get_object_or_404(Classe, slug=slug)
    return HttpResponse("Détails en %s" % (classe.nom,))
