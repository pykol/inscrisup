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

from django.contrib import admin

from parcoursup.models import Etudiant, Classe, Proposition, Action, \
		ParcoursupUser, ParcoursupMessageRecuLog, \
		ParcoursupMessageEnvoyeLog

admin.site.register(Classe)

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

class ActionAdmin(admin.ModelAdmin):
    list_display = ('proposition', 'date', 'categorie', 'etat',
            'message',)

admin.site.register(Action, ActionAdmin)

admin.site.register(ParcoursupUser)
admin.site.register(ParcoursupMessageRecuLog)
admin.site.register(ParcoursupMessageEnvoyeLog)
