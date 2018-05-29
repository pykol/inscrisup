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

from django.db import models
from django.db import transaction
from django.urls import reverse

class EtudiantManager(models.Manager):
    def par_classe(self, classe):
        return self.get_queryset().filter(proposition_actuelle__classe=classe,
            proposition__date_demission__isnull=True,
            proposition__remplacee_par__isnull=True)

class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField("prénom", max_length=100)
    date_naissance = models.DateField("date de naissance", blank=True,
            null=True)
    email = models.EmailField(blank=True, null=False)
    dossier_parcoursup = models.IntegerField("numéro de dossier",
            primary_key=True)
    adresse = models.TextField(blank=True, null=False)
    proposition_actuelle = models.ForeignKey('Proposition', blank=True,
            null=True, related_name='+', on_delete=models.SET_NULL)

    objects = EtudiantManager()

    def __str__(self):
        return "%s %s" % (self.nom, self.prenom,)

    def get_absolute_url(self):
        return reverse('etudiant.details', args=[str(self.pk),])

    class Meta:
        verbose_name = "étudiant"

    @transaction.atomic
    def nouvelle_proposition(self, nouv_prop):
        """Enregistrement d'une nouvelle proposition d'admission.

        Cette méthode enregistre une nouvelle proposition d'admission
        pour un étudiant si cette proposition est différente de ce que
        l'étudiant avait obtenu précédemment (on considère pour cela la
        classe et l'admission à l'internat). Lorsque l'étudiant n'avait
        précédemment aucune proposition, on enregistre simplement la
        nouvelle.

        Cette méthode crée également les actions administrative à
        réaliser suite à cette proposition.
        """
        old_prop = self.proposition_actuelle

        if old_prop and old_prop.classe == nouv_prop.classe and \
                old_prop.internat == nouv_prop.internat:
            if old_prop.statut != nouv_prop.statut:
                old_prop.statut = nouv_prop.statut
                old_prop.save()
            return

        nouv_prop.remplace = old_prop
        nouv_prop.save()

        self.proposition_actuelle = nouv_prop
        self.save()

        if not old_prop:
            Action(proposition=nouv_prop,
                    categorie=Action.ENVOI_DOSSIER,
                    date=nouv_prop.date_proposition).save()
        else:
            # Ajout de la nouvelle proposition et démission de
            # l'ancienne.
            old_prop.date_demission = nouv_prop.date_proposition
            old_prop.save()

            # S'il y a lieu d'enregistrer de nouvelles actions, on le
            # fait immédiatement
            if not old_prop.internat and nouv_prop.internat and \
                    not Action.objects.filter(statut=Action.STATUT_TODO,
                            categorie=Action.ENVOI_DOSSIER,
                            proposition__etudiant=self).exists():
                Action(proposition=nouv_prop,
                        categorie=Action.ENVOI_DOSSIER_INTERNAT,
                        date=nouv_prop.date_proposition).save()

            if old_prop.internat and not nouv_prop.internat:
                for action_envoi in Action.objects.filter(statut=Action.STATUT_TODO,
                        categorie=Action.ENVOI_DOSSIER_INTERNAT,
                        proposition__etudiant=self):
                    action_envoi.annuler(nouv_prop_date.date_proposition)

                Action(proposition=nouv_prop,
                        categorie=Action.INSCRIPTION,
                        date=nouv_prop.date_proposition,
                        message="L'étudiant a renoncé à l'internat").save()

            if old_prop.classe != nouv_prop.classe:
                Action(proposition=nouv_prop,
                        categorie=Action.INSCRIPTION,
                        date=nouv_prop.date_proposition,
                        message="L'étudiant a changé de classe").save()

    @transaction.atomic
    def demission(self, date):
        """Enregistre la démission d'un candidat.

        Cette méthode annule également toutes les actions
        administratives qui n'avaient pas encore été accomplies pour le
        candidat.
        """
        proposition = self.proposition_actuelle
        deja_demission = proposition.date_demission is not None

        proposition.date_demission = date
        proposition.save()

        actions = Action.objects.filter(statut=Action.STATUT_TODO,
                proposition__etudiant=self).exclude(
                        categorie=Action.DEMISSION)
        for action in actions:
            action.annuler(date)

        if not deja_demission:
            Action(proposition=proposition,
                    categorie=Action.DEMISSION,
                    date=date).save()

class Classe(models.Model):
    nom = models.CharField(max_length=20)
    slug = models.SlugField(unique=True)
    code_parcoursup = models.SmallIntegerField()
    groupe_parcoursup = models.SmallIntegerField()
    capacite = models.SmallIntegerField(verbose_name="capacité")
    surbooking = models.SmallIntegerField(default=0)

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('classe.details', args=[self.slug,])

    def admissions(self):
        return Etudiant.objects.par_classe(self)

    def admissions_oui(self):
        return self.admissions().filter(proposition_actuelle__statut=Proposition.STATUT_OUI)

    def admissions_ouimais(self):
        return self.admissions().filter(proposition_actuelle__statut=Proposition.STATUT_OUIMAIS)

class Proposition(models.Model):
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
    etudiant = models.ForeignKey(Etudiant,
            on_delete=models.CASCADE)
    date_proposition = models.DateTimeField()
    date_demission = models.DateTimeField(blank=True, null=True)
    internat = models.BooleanField()
    remplace = models.ForeignKey('self', blank=True, null=True,
            on_delete=models.SET_NULL, related_name='remplacee_par')

    # Prendre les mêmes valeurs que dans l'import Parcoursup
    STATUT_OUI = 0
    STATUT_OUIMAIS = 1
    STATUT_CHOICES = (
            (STATUT_OUI, "Oui définitif"),
            (STATUT_OUIMAIS, "Autres vœux en attente"),
        )
    statut = models.SmallIntegerField(choices=STATUT_CHOICES)

    def __str__(self):
        return str(self.date_proposition)

    class Meta:
        get_latest_by = 'date_proposition'

class Action(models.Model):
    proposition = models.ForeignKey(Proposition,
            on_delete=models.CASCADE)

    ENVOI_DOSSIER = 0
    ENVOI_DOSSIER_INTERNAT = 1
    INSCRIPTION = 2
    DEMANDE_PIECES = 3
    DEMISSION = 4
    CATEGORIE_CHOICES = (
            (ENVOI_DOSSIER, "Envoi du dossier d'inscription"),
            (ENVOI_DOSSIER_INTERNAT, "Envoi du dossier pour l'internat"),
            (INSCRIPTION, "Inscription administrative"),
            (DEMANDE_PIECES, "Demande de pièces complémentaires"),
            (DEMISSION, "Enregistrement d'une démission"),
        )
    categorie = models.SmallIntegerField("catégorie",
            choices=CATEGORIE_CHOICES)

    date = models.DateTimeField()
    date_fait = models.DateTimeField(blank=True, null=True)

    STATUT_TODO = 0
    STATUT_FAIT = 1
    STATUT_RIEN = 2
    STATUT_ANNULEE = 3
    STATUT_CHOICES = (
            (STATUT_TODO, "À traiter"),
            (STATUT_FAIT, "Fait"),
            (STATUT_RIEN, "Rien à faire"),
            (STATUT_ANNULEE, "Annulée"),
        )
    statut = models.SmallIntegerField(choices=STATUT_CHOICES,
            default=STATUT_TODO)

    message = models.TextField(blank=True, null=False)

    def traiter(self, date):
        """Marque une action comme traitée à la date donnée"""
        if self.statut == Action.STATUT_TODO:
            self.date_fait = date
            self.statut = Action.STATUT_FAIT
            self.save()

    def annuler(self, date):
        """Marque une action comme annulée à la date donnée"""
        if self.statut == Action.STATUT_TODO:
            self.date_fait = date
            self.statut = Action.STATUT_ANNULEE
            self.save()

    def est_envoi(self):
        return self.categorie in [Action.ENVOI_DOSSIER,
                Action.ENVOI_DOSSIER_INTERNAT,]
