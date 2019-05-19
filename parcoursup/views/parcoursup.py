# -*- coding: utf-8 -*-

# Inscrisup - Gestion des inscriptions administratives après Parcoursup
# Copyright (c) 2019 Florian Hatat
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

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.utils import timezone

from parcoursup.models import ParcoursupUser, ParcoursupMessageRecuLog, \
		Etudiant, Classe, Proposition
import parcoursup.utils as utils

class ParcoursupClientView(View):
	"""
	Vue générique pour traiter une requête entrante en provenance de
	Parcoursup.

	Elle vérifie que la requête est bien au format JSON et qu'elle
	contient des données d'identification valides. Elle enregistre la
	requête dans le journal des messages Parcoursup.

	Le traitement de la requête elle-même est délégué à la méthode
	self.parcoursup(), qui peut se servir notamment de l'attribut
	self.json, qui contient les données JSON décodées.
	"""
	http_method_names = ['post']
	endpoint = "undef"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.json = None
		self.user = None

	def identification(self):
		"""
		Vérifie que la requête possède bien les données
		d'identification.
		"""
		try:
			self.user = ParcoursupUser.objects.authenticate(
				username=self.json['identifiant']['login'],
				password=self.json['identifiant']['pwd'])
			return True
		except:
			return False

	def entree_json(self):
		"""
		Vérifie que la requête contient bien des données en JSON.
		"""
		if 'application/json' != self.request.content_type:
			return False

		try:
			self.json = json.loads(self.request.body.decode('utf-8'))
			return True
		except (json.JSONDecodeError, UnicodeDecodeError):
			return False

	def json_response(self, ok, message=None, status_code=None):
		"""
		Construction d'une réponse pour Parcoursup
		"""
		data = {
			'message': message
		}

		if ok:
			data['retour'] = 'OK'

			if data['message'] is None:
				data['message'] = "Requete correctement traitee"

			status_code = status_code if status_code is not None else 200
		else:
			data['retour'] = 'NOK'

			if data['message'] is None:
				data['message'] = "Erreur lors du traitement"

			status_code = status_code if status_code is not None else 500

		response = JsonResponse(data)
		response.status_code = status_code
		return response

	# On redéfinit cette méthode uniquement afin de la décorer, car les
	# appels de l'API REST ne doivent pas être protégés par le jeton
	# CSRF de Django.
	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get_ip_source(self):
		"""
		Détermine l'IP à l'origine de la requête
		"""
		try:
			return self.request.META['HTTP_X_FORWARDED_FOR'].split(',')[0]
		except:
			return self.request.META['REMOTE_ADDR']

	def post(self, request):
		"""
		Traitement des données issues d'une requête POST provenant de
		Parcoursup.

		Cette méthode vérifie que les données sont au format JSON et que
		la requête possède des informations d'identification valides,
		puis confie le reste du traitement à la méthode
		self.parcoursup(). Cette dernière doit renvoyer elle-même la
		réponse au format JSON, en s'aidant éventuellement de la méthode
		self.json_response(). Si elle lève une exception, une réponse
		d'erreur générique est renvoyée à Parcoursup.
		"""
		msg_log = ParcoursupMessageRecuLog(date=timezone.now(),
				ip_source=selF.get_ip_source(),
				endpoint=self.endpoint)

		if not self.entree_json():
			msg_log.message = "Les données soumises ne sont pas au format JSON valide"
			msg_log.save()
			return self.json_response(False, msg_log.message)

		if not self.identification():
			msg_log.message = "Données d'identification incorrectes"
			msg_log.save()
			return self.json_response(False, msg_log.message)

		msg_log.user = self.user

		try:
			response = self.parcoursup()
		except:
			response = self.json_response(False)

		msg_log.succes = response.get('retour', 'NOK') == 'OK'
		msg_log.message = response.get('message', "")
		msg_log.save()
		return response

class AdmissionView(ParcoursupClientView):
	"""
	Vue appelée par Parcoursup pour transmettre la réponse d'un candidat
	à une proposition d'admission.
	"""
	endpoint = "admissionCandidat"

	def parcoursup(self):
		donnees = self.json['donneesCandidat']

		etudiant, _ = Etudiant.objects.update_or_create(
			dossier_parcoursup = donnees['codeCandidat'],
			defaults={
				'nom': donnees['nom'],
				'prenom': donnees['prenom'],
				'date_naissance': utils.parse_date(donnees['dateNaissance']),
				'email': donnees['mail'],
				'telephone': donnees.get('telfixe'),
				'telephone_mobile': donnees.get('telmobile'),
				'adresse': utils.format_adresse_pays(
						adresse1=donnees['adresse1'],
						adresse2=donnees['adresse2'],
						code_postal=donnees['codePostal'],
						ville=donnees['libelleCommune'],
						pays=donnees['codePaysadresse'],
					),
				'sexe': Etudiant.SEXE_HOMME if donnees['sexe'] == 'M' \
						else Etudiant.SEXE_FEMME
			})

		# On détermine la proposition à laquelle fait référence le
		# message actuel.
		classe = Classe.objects.get(code_parcoursup=donnees['codeFormationPsup'])
		date_reponse = utils.parse_datetime(donnees['dateReponse'])
		proposition = Proposition(
			etudiant=etudiant,
			classe=classe,
			date_proposition=date_reponse,
			cesure=donnees.get('cesure', 0) == 1,
			internat=donnees.get('internat', 0) == 1,
			inscription=donnees.get('etatInscription', 0) == 1,
		)

		# Le candidat n'a pas encore répondu
		if donnees['codeSituation'] == 0:
			# On n'enregistre dans la base de données que les candidats
			# qui ont accepté la formation. Ce message provenant de
			# Parcoursup est donc ignoré. La proposition sera
			# enregistrée lorsque Parcoursup nous enverra la réponse
			# positive.
			pass

		# Proposition acceptée définitivement
		if donnees['codeSituation'] == 1:
			proposition.etat = Proposition.ETAT_OUI
			etudiant.nouvelle_proposition(proposition)

		# Proposition acceptée avec autres vœux en attente
		if donnees['codeSituation'] == 2:
			proposition.etat = Proposition.ETAT_OUIMAIS
			etudiant.nouvelle_proposition(proposition)

		# Proposition refusée
		if donnees['codeSituation'] == 3:
			proposition = Proposition.objects.get(
				etudiant=etudiant, classe=classe,
				cesure=proposition.cesure,
				internat=proposition.internat)
			proposition.demission(date_reponse)

		return self.json_response(True)
