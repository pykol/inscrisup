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
from django.urls import reverse

class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField("prénom", max_length=100)
    date_naissance = models.DateField("date de naissance")
    email = models.EmailField(blank=True, null=False)
    dossier_parcoursup = models.IntegerField("numéro de dossier",
            primary_key=True)

    def __str__(self):
        return "%s %s" % (self.nom, self.prenom,)

    def get_absolute_url(self):
        return reverse('etudiant.details', args=[str(self.pk),])

    class Meta:
        verbose_name = "étudiant"

class Classe(models.Model):
    nom = models.CharField(max_length=20)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('classe.details', args=[self.slug,])

class Proposition(models.Model):
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
    etudiant = models.ForeignKey(Etudiant,
            on_delete=models.CASCADE)
    date_proposition = models.DateTimeField()
    date_demission = models.DateTimeField(blank=True, null=True)
    internat = models.BooleanField()
    remplace = models.ForeignKey('self', blank=True, null=True,
            on_delete=models.SET_NULL)

    STATUT_OUI = 0
    STATUT_OUIMAIS = 1
    STATUT_CHOICES = (
            (STATUT_OUI, "Oui définitif"),
            (STATUT_OUIMAIS, "Autres vœux en attente"),
        )
    statut = models.SmallIntegerField(choices=STATUT_CHOICES)

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
    STATUT_CHOICES = (
            (STATUT_TODO, "À traiter"),
            (STATUT_FAIT, "Fait"),
            (STATUT_RIEN, "Rien à faire"),
        )
    statut = models.SmallIntegerField(choices=STATUT_CHOICES)
