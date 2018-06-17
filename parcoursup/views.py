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

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views import generic
from django.urls import reverse
from django.db.models import Count, Q, F
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Classe, Etudiant, Action, Proposition, \
        ParcoursupSynchro
from .forms import PropositionForm, ParcoursupImportForm
from .pdf_adresses import pdf_adresses
from .odf_liste import par_classe as odf_par_classe

@login_required
def index(request):
    classe_list = Classe.objects.all().annotate(
            num_admis=Count('proposition',
                filter=Q(proposition__date_demission__isnull=True,
                    proposition__remplacee_par__isnull=True)))
    props_internat = Proposition.objects.filter(
            remplacee_par__isnull=True,
            date_demission__isnull=True,
            internat=True
            )

    num_internat = props_internat.count()
    num_internat_oui = \
            props_internat.filter(statut=Proposition.STATUT_OUI).count()
    num_internat_ouimais = \
            props_internat.filter(statut=Proposition.STATUT_OUIMAIS).count()

    synchro_list = ParcoursupSynchro.objects.all().order_by('-date_debut')[:5].annotate(duree=F('date_fin')
            - F('date_debut'))

    return render(request, 'parcoursup/index.html', context={
        'classe_list': classe_list,
        'num_internat': num_internat,
        'num_internat_oui': num_internat_oui,
        'num_internat_ouimais': num_internat_ouimais,
        'synchro_list': synchro_list,
        })

class ClasseDetailView(LoginRequiredMixin, generic.DetailView):
    model = Classe

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classe = self.get_object()
        context['etudiant_list'] = classe.admissions().order_by('nom')
        return context

class EtudiantDetailView(LoginRequiredMixin, generic.DetailView):
    model = Etudiant

@login_required
def proposition_ajout(request):
    if request.method == 'POST':
        form = PropositionForm(request.POST)
        if form.is_valid():
            form.save()
            etudiant = Etudiant.objects.get(pk=form.data['etudiant'])
            return redirect(etudiant)
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

@login_required
def etudiant_demission(request, pk):
    etudiant = get_object_or_404(Etudiant, pk=pk)
    etudiant.demission(datetime.datetime.now())

    return redirect('etudiant.details', pk=etudiant.pk)

class ActionTodoListView(LoginRequiredMixin, generic.ListView):
    queryset = Action.objects.filter(
            statut = Action.STATUT_TODO).order_by('proposition__statut',
                    'proposition__etudiant__nom')

class ActionDetailView(LoginRequiredMixin, generic.DetailView):
    model = Action

@login_required
def action_traiter(request, pk):
    action = get_object_or_404(Action, pk=pk)
    action.traiter(datetime.datetime.now())
    return redirect('action.liste')

@login_required
def parcoursup_import(request):
    if request.method == 'POST':
        form = ParcoursupImportForm(request.POST, request.FILES)
        if form.is_valid():
            dossiers_dans_fichier = []
            #TODO traitement du fichier Parcoursup
            for ligne in fichier:
                numero = int(ligne[0])
                try:
                    etudiant = Etudiant.objects.get(pk=numero)
                except Etudiant.DoesNotExist:
                    etudiant = Etudiant(
                            dossier_parcoursup=numero,
                            nom=ligne[1],
                            prenom=ligne[2],
                            date_naissance=ligne[3],
                            email=ligne[4])
                    etudiant.save()

                classe = Classe.objects.get(nom=ligne[5])
                internat = ligne[6]

                proposition = Proposition(
                        classe=classe,
                        etudiant=etudiant,
                        date_proposition=datetime.datetime.now(),#XXX fichier ?
                        internat=internat,
                        statut=ligne[7])

                etudiant.nouvelle_proposition(proposition)

                dossiers_dans_fichier.append(numero)

            demissionnaires = Etudiant.objects.filter(dossier_parcoursup__not_in=dossiers_dans_fichier)
            for dem in demissionnaires:
                dem.demission(datetime.datetime.now())
    else:
        form = ParcoursupImportForm()

    return render(request, 'parcoursup/parcoursup_import.html',
            {
                'form': form,
            })

@login_required
def parcoursup_auto_import(request):
    from .import_parcoursup import auto_import
    auto_import()
    return redirect('index')

@login_required
def export_pdf_adresses(request):
    etudiants = Etudiant.objects.filter(
            proposition__action__statut=Action.STATUT_TODO,
            proposition__action__categorie__in=(Action.ENVOI_DOSSIER,
                Action.ENVOI_DOSSIER_INTERNAT)).order_by('nom')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="adresses_parcoursup.pdf"'
    pdf_adresses(etudiants, response)

    return response

@login_required
def export_pdf_adresses_definitif(request):
    etudiants = Etudiant.objects.filter(
            proposition__statut=Proposition.STATUT_OUI,
            proposition__action__statut=Action.STATUT_TODO,
            proposition__action__categorie__in=(Action.ENVOI_DOSSIER,
                Action.ENVOI_DOSSIER_INTERNAT))
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="adresses_parcoursup.pdf"'
    pdf_adresses(etudiants, response)

    return response

@login_required
def export_pdf_adresse_etudiant(request, pk):
    etudiant = Etudiant.objects.filter(pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="adresses_parcoursup.pdf"'
    pdf_adresses(etudiant, response)

    return response

@login_required
def internat_detail(request):
    etudiant_list = Etudiant.objects.filter(
            proposition_actuelle__internat=True,
            proposition_actuelle__remplacee_par__isnull=True,
            proposition_actuelle__date_demission__isnull=True)

    num_hommes = etudiant_list.filter(sexe=Etudiant.SEXE_HOMME).count()
    num_femmes = etudiant_list.filter(sexe=Etudiant.SEXE_FEMME).count()

    par_classe_qs = \
            etudiant_list.values('proposition_actuelle__classe').annotate(Count('dossier_parcoursup'))

    par_classe = {}
    for item in par_classe_qs:
        classe = Classe.objects.get(pk=item['proposition_actuelle__classe'])
        num = item['dossier_parcoursup__count']
        par_classe[classe] = num

    return render(request, 'parcoursup/internat_detail.html',
            context={
                'etudiant_list': etudiant_list,
                'num_hommes': num_hommes,
                'num_femmes': num_femmes,
                'par_classe': par_classe,
                })

@login_required
def export_odf_classes(request):
    response = HttpResponse(content_type='application/vnd.oasis.opendocument.spreadsheet')
    response['Content-Disposition'] = 'attachment; filename="liste_classes.ods"'
    odf_par_classe(Classe.objects.all().order_by('nom'), response)
    return response
