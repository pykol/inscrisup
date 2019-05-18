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

from inscrisup.models import ParcoursupUser

class ParcoursupClientView(View):
	http_method_names = ['post']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.identification = None
		self.json = None
		self.message_retour = None
		self.status_code = None
		self.user = None

	def identification(self):
		"""
		Vérifie que la requête possède bien les données
		d'identification.
		"""
		try:
			self.user = ParcoursupUser.objects.login(
				username=self.json['identifiant']['login'],
				password=self.json['identifiant']['pwd'])
			return True
		except:
			return False

	def entree_json(self):
		"""
		Vérifie que la requête contient bien des données en JSON.
		"""
		if 'application.json' != self.request.content_type:
			return False

		try:
			self.json = json.loads(self.request.body.decode('utf-8'))
		except (json.JSONDecodeError, UnicodeDecodeError):
			return False

	def json_reponse(self, ok, message):
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

			status_code = self.status_code \
				if self.status_code is not None else 200
		else:
			data['retour'] = 'NOK'

			if data['message'] is None:
				data['message'] = "Erreur lors du traitement"

			status_code = self.status_code \
				if self.status_code is not None else 500

		return JsonResponse(data, status_code=status_code)

	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def post(self):
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
		if not self.entree_json():
			return self.json_response(False,
				"Les données soumises ne sont pas au format JSON valide")

		if not self.identification():
			return self.json_response(False,
				"Données d'identification incorrectes")

		try:
			return self.parcoursup()
		except:
			return self.json_response(False)

def AdmissionView(ParcoursupClientView):
	def parcoursup(self):
		pass
