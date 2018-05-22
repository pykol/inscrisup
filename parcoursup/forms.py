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

from django import forms

from .models import Proposition

class PropositionForm(forms.ModelForm):
    class Meta:
        model = Proposition
        fields = ['classe', 'etudiant', 'date_proposition', 'internat',
                'statut']

    def save(self, commit=False):
        nouv_prop = super(PropositionForm, self).save(commit=commit)
        if nouv_prop:
            nouv_prop.etudiant.nouvelle_proposition(nouv_prop)
        return nouv_prop
