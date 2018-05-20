# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Etudiant, Classe, Proposition, Action

admin.site.register(Etudiant)
admin.site.register(Classe)
admin.site.register(Proposition)
admin.site.register(Action)
