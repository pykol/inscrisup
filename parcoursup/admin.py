# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Etudiant, Classe, Proposition, Action

admin.site.register(Classe)
admin.site.register(Action)

class PropositionAdmin(admin.ModelAdmin):
    list_display = ('date_proposition', 'classe', 'etudiant',
            'internat',)
    list_filter = ['classe',]
admin.site.register(Proposition, PropositionAdmin)


class PropositionInline(admin.TabularInline):
    model = Proposition
    extra = 1

class EtudiantAdmin(admin.ModelAdmin):
    inlines = [PropositionInline]

admin.site.register(Etudiant, EtudiantAdmin)
