# -*- coding: utf-8 -*-
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
