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

"""
Utilitaires pour communiquer avec l'API REST de Parcoursup
"""

from datetime import date
import requests

PARCOURSUP_ENDPOINT = "https://ws.parcoursup.fr/ApiRest/"

class ParcoursupRequest:
	"""
	Légère couche d'abstraction au-dessus du module requests pour gérer
	l'envoi de requêtes à l'API Parcoursup, en incluant les données
	d'identification.
	"""
	def __init__(self, login, password, method_name=None,
			http_method='POST', data={}):
		self.login = login
		self.password = password
		self.response = None
		self.method_name = method_name
		self.http_method = http_method

		self.data = data
		self.data.update({
			# Oui, il y a une faute de frappe dans l'API Parcoursup
			'indentifiant': {
				'login': login,
				'pwd': password,
			}
		})

	def get_url(self):
		"""
		Construction de l'URL à laquelle il faut poster la requête.
		"""
		return '{base}{method}'.format(
			base=PARCOURSUP_ENDPOINT, method=self.method_name)

	def send(self):
		"""
		Envoi de la requête à Parcoursup.
		"""
		# Oui, ça a l'air idiot, mais c'est pour plus tard si jamais
		# Parcoursup nous introduit d'autres méthodes HTTP dans des
		# mises à jour de l'API.
		if self.http_method != 'POST':
			raise ValueError("Cette API ne gère pas d'autres méthodes "
					"HTTP que POST")

		self.request = requests.post(self.get_url(), json=self.data)

class ParcoursupCandidat:
	def __init__(self, code, nom, prenom, date_naissance, ine):
		self.code = code
		self.nom = nom
		self.prenom = prenom
		self.date_naissance = date_naissance
		self.ine = ine

	def to_json(self):
		return {
			'codeCandidat': int(self.code),
			'ine': str(self.ine),
			'nom': str(self.nom),
			'prenom': str(self.prenom),
			'dateNaissance': self.date_naissance.strftime('%d/%m/%Y')
		}

class ParcoursupRest:
	def __init__(self, login, password, code_etablissement):
		self.login = login
		self.password = password
		self.code_etablissement = code_etablissement

	def get_candidats_admis(self, **kwargs):
		"""
		Accès générique à la méthode getCandidatsAdmis de l'API
		Parcoursup.

		Cette méthode est déclinée en autres méthodes plus simples à
		utiliser, en fonction des paramètres que l'on veut renseigner.
		"""
		parcoursup_args = {
			'code_candidat': ('codeCandidat', int),
			'formation': ('codeFormationpsup', int),
			'formation1': ('codeFormation1', str),
			'formation2': ('codeFormation2', str),
			'formation3': ('codeFormation3', str),
			'formation4': ('codeFormation4', str),
			'code_sise': ('codeSISE': str),
		}
		request_data = {
			'codeEtablissement': str(self.code_etablissement)
		}
		args_inconnus = []
		for kwarg, valeur in kwargs.items():
			try:
				psup_arg, coercion = parcoursup_args[kwarg]
				request_data[psup_arg] = coercion(valeur)
			except KeyError as e:
				args_inconnus.append(e.args[0])
		if args_inconnus:
			raise TypeError("Unexpected named parameters {}".format(
				', '.join(args_inconnus)))

		request = ParcoursupRequest(self.login, self.password,
				method_name='getCandidatsAdmis',
				data=request_data)
		request.send()
		return request

	def get_candidat(self, code_candidat):
		"""
		Recherche des informations sur un candidat admis d'après son
		numéro de dossier.
		"""
		return self.get_candidats_admis(self, code_candidat=code_candidat)


	# Codes des statuts d'inscription de l'API Parcoursup
	INSCRIPTION_PRINCIPALE = 1
	INSCRIPTION_DOUBLE_CURSUS = 2
	INSCRIPTION_ANNULEE = 3
	INSCRIPTION_PARALLELE = 4
	INSCRIPTION_PARALLELE_SECONDAIRE = 5

	def maj_inscription(self, candidat, formation,
			code_sise, statut_inscription):
		"""
		Mise à jour du statut d'inscription d'un candidat.
		"""
		request_data = candidat.to_json()
		request_data.update({
			'codeFormationPsup': int(formation),
			'codeFormation1': str(formation),
			'codeSISE': str(code_sise),
			'codeStatutInscription': int(statut_inscription),
			'etatInscription': int(statut_inscription),
			'codeEtablissementAffectation': str(self.code_etablissement),
		})
		request = ParcoursupRequest(self.login, self.password,
				method_name='majInscriptionAdministrative',
				data=request_data)
		request.send()
		return request

	def requete_test(self):
		"""
		Envoie la requête test prévue par Parcoursup. Cette requête doit
		être envoyée avant d'avoir accès à l'API d'admission.
		"""
		candidat = ParcoursupCandidat(
			code=1, nom="Bernard", prenom="Minet",
			date_naissance=date(1789, 7, 14),
			ine="0123456789AB")

		return self.maj_inscription(candidat=candidat,
			formation=42, code_sise=1,
			statut_inscription=INSCRIPTION_PRINCIPALE)
