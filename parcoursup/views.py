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
from django.db.models import Count, Q

from .models import Classe, Etudiant, Action, Proposition
from .forms import PropositionForm, ParcoursupImportForm
from .import_parcoursup import Parcoursup
from .pdf_adresses import pdf_adresses

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

    return render(request, 'parcoursup/index.html', context={
        'classe_list': classe_list,
        'num_internat': num_internat,
        'num_internat_oui': num_internat_oui,
        'num_internat_ouimais': num_internat_ouimais,
        })

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

def etudiant_demission(request, pk):
    etudiant = get_object_or_404(Etudiant, pk=pk)
    etudiant.demission(datetime.datetime.now())

    return redirect('etudiant.details', pk=etudiant.pk)

class ActionTodoListView(generic.ListView):
    queryset = Action.objects.filter(statut = Action.STATUT_TODO)

class ActionDetailView(generic.DetailView):
    model = Action

def action_traiter(request, pk):
    action = get_object_or_404(Action, pk=pk)
    action.traiter(datetime.datetime.now())
    return redirect('action.liste')

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

def parcoursup_auto_import(request):
    psup = Parcoursup()
    psup.connect('utilisateur_parcoursup', 'mot_de_passe')

    # Import des propositions d'admission depuis Parcoursup
    candidats = {}
    for classe in Classe.objects.all():
        if classe.code_parcoursup > 0 and classe.groupe_parcoursup > 0:
            for (etat, _) in Parcoursup.ETAT_CHOICES:
                psup.recupere_par_etat(classe, etat, candidats)

    # Import des adresses des candidats depuis les fichiers d'admission
    adresses = {}
    for classe in Classe.objects.all():
        if classe.code_parcoursup > 0:
            adresses.update(psup.fichier_admissions(classe))

    psup.disconnect()

    # Enregistrer les propositions en base de données
    for numero in candidats:
        psup_prop = candidats[numero]

        try:
            etudiant = Etudiant.objects.get(pk=numero)
        except Etudiant.DoesNotExist:
            # On ignore simplement les étudiants démissionnaires qui
            # n'étaient pas encore créés dans la base de données.
            if psup_prop.etat == Parcoursup.ETAT_DEMISSION:
                continue

            # Dans tous les autres cas, on importe l'étudiant quand il
            # n'existe pas encore.
            etudiant = Etudiant(
                    dossier_parcoursup=numero,
                    nom=psup_prop.nom,
                    prenom=psup_prop.prenom)
            etudiant.save()

        if psup_prop.etat != Parcoursup.ETAT_DEMISSION:
            proposition = Proposition(
                    classe=psup_prop.classe,
                    etudiant=etudiant,
                    date_proposition=psup_prop.date_proposition,
                    internat=psup_prop.internat,
                    statut=psup_prop.etat,
                    )
            etudiant.nouvelle_proposition(proposition)
        else:
            etudiant.demission(psup_prop.date_reponse)

    # Enregistrer les adresses des candidats
    for numero in adresses:
        Etudiant.objects.filter(pk=numero).update(**adresses[numero])

    return redirect('index')

def export_pdf_adresses(request):
    actions = Action.objects.filter(statut=Action.STATUT_TODO,
            categorie__in=(Action.ENVOI_DOSSIER,
                Action.ENVOI_DOSSIER_INTERNAT))
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="adresses_parcoursup.pdf"'
    pdf_adresses(actions, response)

    return response

def internat_detail(request):
    etudiant_list = Etudiant.objects.filter(
            proposition_actuelle__internat=True,
            proposition_actuelle__remplacee_par__isnull=True,
            proposition_actuelle__date_demission__isnull=True)
    return render(request, 'parcoursup/internat_detail.html',
            context={'etudiant_list': etudiant_list})
