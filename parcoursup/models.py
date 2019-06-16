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
from django.contrib.auth.hashers import check_password

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
	telephone = models.CharField(verbose_name="téléphone",
			max_length=20, blank=True, null=False)
	telephone_mobile = models.CharField(verbose_name="téléphone mobile",
			max_length=20, blank=True, null=False)
	dossier_parcoursup = models.IntegerField("numéro de dossier",
			primary_key=True)
	adresse = models.TextField(blank=True, null=False)
	proposition_actuelle = models.ForeignKey('Proposition', blank=True,
			null=True, related_name='+', on_delete=models.SET_NULL)

	SEXE_HOMME=1
	SEXE_FEMME=2
	SEXE_CHOICES = (
			(SEXE_HOMME, 'M.'),
			(SEXE_FEMME, 'Mme'),
		)
	sexe = models.SmallIntegerField(choices=SEXE_CHOICES, blank=True,
			null=True)

	objects = EtudiantManager()

	def __str__(self):
		return "%s %s" % (self.nom, self.prenom,)

	def get_absolute_url(self):
		return reverse('etudiant.details', args=[str(self.pk),])

	def civilite(self):
		if self.sexe:
			if self.sexe == Etudiant.SEXE_HOMME:
				return 'M.'
			else:
				return 'Mme'

	class Meta:
		verbose_name = "étudiant"

	@transaction.atomic
	def nouvelle_proposition(self, nouv_prop):
		"""
		Enregistrement d'une nouvelle proposition d'admission.

		Cette méthode enregistre une nouvelle proposition d'admission
		pour un étudiant si cette proposition est différente de ce que
		l'étudiant avait obtenu précédemment (on considère pour cela la
		classe et l'admission à l'internat). Lorsque l'étudiant n'avait
		précédemment aucune proposition, on enregistre simplement la
		nouvelle.

		Cette méthode crée également les actions administratives à
		réaliser suite à cette proposition.
		"""
		old_prop = self.proposition_actuelle

		actions_demission = Action.objects.filter(
			etudiant=self,
			categorie=Action.DEMISSION,
			etat=Action.ETAT_TODO)

		# On annule les démissions précédentes.
		for action in actions_demission:
			action.annuler(nouv_prop.date_proposition)

		# Dans le cas où la nouvelle proposition correspond en fait à
		# l'ancienne, mais seul l'état a changé (passant de oui mais à
		# oui définitif), on enregistre seulement le changement d'état.
		if old_prop and old_prop.classe == nouv_prop.classe and \
				old_prop.internat == nouv_prop.internat:
			if old_prop.etat != nouv_prop.etat:
				old_prop.etat = nouv_prop.etat
				old_prop.save()
			return

		nouv_prop.remplace = old_prop
		nouv_prop.save()

		self.proposition_actuelle = nouv_prop
		self.save()

		# On envoie le dossier d'inscription s'il n'a pas encore été
		# envoyé.
		try:
			action_dossier = self.action_set.get(
				etat__in=(Action.ETAT_TODO, Action.ETAT_FAIT),
				categorie=Action.ENVOI_DOSSIER)
		except Action.DoesNotExist:
			action_dossier = Action(categorie=Action.ENVOI_DOSSIER,
					etudiant=self,
					date=nouv_prop.date_proposition,
					proposition=nouv_prop)
			action_dossier.save()

		if old_prop:
			# Ajout de la nouvelle proposition et démission de
			# l'ancienne.
			old_prop.date_demission = nouv_prop.date_proposition
			old_prop.save()

			# On rattache toutes les actions d'envoi pas encore traitées
			# à la proposition actuelle.
			self.action_set.filter(etat=Action.ETAT_TODO,
					categorie__in=(Action.ENVOI_DOSSIER,
						Action.ENVOI_DOSSIER_INTERNAT)
					).update(proposition=nouv_prop)

			# Envoi du dossier complémentaire d'internat si le reste du
			# dossier a déjà été envoyé lors d'une proposition
			# précédente.
			if not old_prop.internat and nouv_prop.internat and \
					not Action.objects.filter(etat=Action.ETAT_TODO,
							categorie=Action.ENVOI_DOSSIER,
							proposition__etudiant=self).exists():
				Action(proposition=nouv_prop,
						etudiant=self,
						categorie=Action.ENVOI_DOSSIER_INTERNAT,
						date=nouv_prop.date_proposition).save()

			# Si l'étudiant a renoncé à l'internat, on retire les envois
			# de dossier d'internat.
			if old_prop.internat and not nouv_prop.internat:
				for action_envoi in Action.objects.filter(etat=Action.ETAT_TODO,
						categorie=Action.ENVOI_DOSSIER_INTERNAT,
						proposition__etudiant=self):
					action_envoi.annuler(nouv_prop_date.date_proposition)

				Action(proposition=nouv_prop,
						etudiant=self,
						categorie=Action.INSCRIPTION,
						date=nouv_prop.date_proposition,
						message="L'étudiant a renoncé à l'internat").save()

			# Enregistrement d'un changement de classe.
			# Le cas du changement de classe peut aussi se produire si
			# l'étudiant a démissionné par le passé et a dit oui à une
			# nouvelle proposition. Dans ce cas, on annule l'action
			# pour prendre en compte la démission, si elle n'a pas déjà
			# été traitée.
			if old_prop.classe != nouv_prop.classe or \
					actions_demission.exclude(proposition__classe=nouv_prop.classe):
				Action(proposition=nouv_prop,
						etudiant=self,
						categorie=Action.INSCRIPTION,
						date=nouv_prop.date_proposition,
						message="L'étudiant a changé de classe").save()

	@transaction.atomic
	def demission(self, date):
		"""
		Enregistre la démission d'un candidat.

		Cette méthode annule également toutes les actions
		administratives qui n'avaient pas encore été accomplies pour le
		candidat.
		"""
		proposition = self.proposition_actuelle
		proposition.demission(date)

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
		return self.admissions().filter(proposition_actuelle__etat=Proposition.ETAT_OUI)

	def admissions_ouimais(self):
		return self.admissions().filter(proposition_actuelle__etat=Proposition.ETAT_OUIMAIS)

class Proposition(models.Model):
	"""
	Une proposition d'admission d'un étudiant par Parcoursup
	"""
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	etudiant = models.ForeignKey(Etudiant,
			on_delete=models.CASCADE)
	date_proposition = models.DateTimeField()
	date_demission = models.DateTimeField(blank=True, null=True)
	internat = models.BooleanField()
	remplace = models.ForeignKey('self', blank=True, null=True,
			on_delete=models.SET_NULL, related_name='remplacee_par')
	cesure = models.BooleanField(verbose_name="césure")

	# Prendre les mêmes valeurs que dans l'import Parcoursup
	ETAT_OUI = 0
	ETAT_OUIMAIS = 1
	ETAT_CHOICES = (
			(ETAT_OUI, "Oui définitif"),
			(ETAT_OUIMAIS, "Autres vœux en attente"),
		)
	etat = models.SmallIntegerField(choices=ETAT_CHOICES)

	# État de l'inscription administrative au lycée
	inscription = models.BooleanField(verbose_name="inscription réalisée")

	def __str__(self):
		return str(self.date_proposition)

	def demission(self, date):
		"""
		Enregistre la démission d'un candidat sur cette proposition.
		"""
		deja_demission = self.date_demission is not None
		self.date_demission = date
		self.save()

		actions = self.action_set.filter(etat=Action.ETAT_TODO
			).exclude(categorie=Action.DEMISSION)
		for action in actions:
			action.annuler(date)

		if not deja_demission:
			Action(proposition=self,
					categorie=Action.DEMISSION,
					etudiant=self.etudiant,
					date=date).save()

		if self == self.etudiant.proposition_actuelle:
			self.etudiant.proposition_actuelle = None
			self.etudiant.save()

	class Meta:
		get_latest_by = 'date_proposition'

class Action(models.Model):
	"""
	Action à réaliser par le secrétariat suite à une modification sur
	des propositions d'admission.
	"""

	# Proposition Parcoursup à l'origine de cette action
	proposition = models.ForeignKey(Proposition,
			on_delete=models.SET_NULL, blank=True, null=True)

	# Étudiant concerné par cette action
	etudiant = models.ForeignKey(Etudiant, verbose_name="étudiant",
			on_delete=models.CASCADE)

	ENVOI_DOSSIER = 0
	ENVOI_DOSSIER_INTERNAT = 1
	INSCRIPTION = 2
	DEMANDE_PIECES = 3
	DEMISSION = 4
	CESURE = 5
	CATEGORIE_CHOICES = (
			(ENVOI_DOSSIER, "Envoi du dossier d'inscription"),
			(ENVOI_DOSSIER_INTERNAT, "Envoi du dossier pour l'internat"),
			(INSCRIPTION, "Inscription administrative"),
			(DEMANDE_PIECES, "Demande de pièces complémentaires"),
			(DEMISSION, "Enregistrement d'une démission"),
			(CESURE, "Traiter la demande de césure"),
		)
	categorie = models.SmallIntegerField("catégorie",
			choices=CATEGORIE_CHOICES)

	date = models.DateTimeField()
	date_fait = models.DateTimeField(blank=True, null=True)

	ETAT_TODO = 0
	ETAT_FAIT = 1
	ETAT_RIEN = 2
	ETAT_ANNULEE = 3
	ETAT_CHOICES = (
			(ETAT_TODO, "À traiter"),
			(ETAT_FAIT, "Fait"),
			(ETAT_RIEN, "Rien à faire"),
			(ETAT_ANNULEE, "Annulée"),
		)
	etat = models.SmallIntegerField(choices=ETAT_CHOICES,
			default=ETAT_TODO)

	message = models.TextField(blank=True, null=False)

	def traiter(self, date):
		"""Marque une action comme traitée à la date donnée"""
		if self.etat == Action.ETAT_TODO:
			self.date_fait = date
			self.etat = Action.ETAT_FAIT
			self.save()

	def annuler(self, date):
		"""Marque une action comme annulée à la date donnée"""
		if self.etat == Action.ETAT_TODO:
			self.date_fait = date
			self.etat = Action.ETAT_ANNULEE
			self.save()

	def est_envoi(self):
		return self.categorie in [Action.ENVOI_DOSSIER,
				Action.ENVOI_DOSSIER_INTERNAT,]

class ParcoursupSynchro(models.Model):
	date_debut = models.DateTimeField(verbose_name="début")
	date_fin = models.DateTimeField(verbose_name="fin")

	MODE_AUTO = 1
	MODE_MANUEL = 2
	MODE_CHOICES = (
			(MODE_AUTO, "Automatique"),
			(MODE_MANUEL, "Manuelle"),
		)
	mode = models.SmallIntegerField(choices=MODE_CHOICES)

	RESULTAT_OK = 1
	RESULTAT_ERREUR = 2
	RESULTAT_CHOICES = (
			(RESULTAT_OK, "Réussie"),
			(RESULTAT_ERREUR, "Échec"),
		)
	resultat = models.SmallIntegerField(verbose_name="résultat",
			choices=RESULTAT_CHOICES, blank=True, null=True)

	SOURCE_WEBSCRAP = 1
	SOURCE_REST = 2
	SOURCE_CHOICES = (
		(SOURCE_WEBSCRAP, "extraction web"),
		(SOURCE_REST, "interface synchrone"),
	)
	source = models.SmallIntegerField(verbose_name="source des données",
			choices=SOURCE_CHOICES)

class ParcoursupUserManager(models.Manager):
	def authenticate(self, username, password):
		"""
		Renvoie l'utilisateur désigné par le nom d'utilisateur et le mot
		de passe donnés en paramètre.

		Lève l'exception ParcoursupUser.DoesNotExist si l'utilisateur
		n'existe pas ou si le mot de passe n'est pas correct.
		"""
		user = self.get(username=username)
		if not user.check_password(password):
			raise user.DoesNotExist

		return user

class ParcoursupUser(models.Model):
	username = models.CharField(max_length=50)
	password = models.CharField(max_length=128)

	objects = ParcoursupUserManager()

	def check_password(self, raw_password):
		"""
		Renvoie True lorsque le mot de passe en clair correspond à celui
		de l'utilisateur.
		"""
		def setter(raw_password):
			self.password = make_password(raw_password)
			self.save(update_fields=["password"])

		if not check_password(raw_password, self.password, setter):
			# En cas d'échec, on ralentit le retour pour prendre à peu
			# près le même temps que si setter avait été appelé.
			make_password(raw_password)
			return False

		return True

class ParcoursupMessageRecuLog(models.Model):
	"""
	Journal des messages reçus depuis Parcoursup
	"""
	date = models.DateTimeField()
	ip_source = models.GenericIPAddressField()
	user = models.ForeignKey(ParcoursupUser, on_delete=models.SET_NULL,
			blank=True, null=True)
	endpoint = models.CharField(max_length=100)
	message = models.CharField(max_length=200)
	succes = models.BooleanField()
	payload = models.BinaryField(verbose_name="données reçues",
			blank=True, default=b'', null=True)

class ParcoursupMessageEnvoyeLog(models.Model):
	"""
	Journal des messages envoyés à Parcoursup
	"""
	date = models.DateTimeField()

class Commune(models.Model):
	"""
	Commune française, identifiée par son code INSEE.
	"""
	insee = models.CharField(max_length=5, primary_key=True)
	libelle = models.CharField(max_length=200)
