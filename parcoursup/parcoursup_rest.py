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

from datetime import date, datetime
import re
import requests
from dateutil.tz import gettz

from django.utils import timezone
from django.conf import settings

from parcoursup.models import Commune, Classe, Etudiant, \
		Proposition, ParcoursupSynchro
from parcoursup.utils import parse_french_date

PARCOURSUP_ENDPOINT = "https://ws.parcoursup.fr/ApiRest/"

def parse_date_reponse(date_str):
	paris_tz = gettz('Europe/Paris')
	date_match = re.match('^(?P<jour>\d{1,2})/(?P<mois>\d{1,2})/(?P<annee>\d{3}) (?P<heure>\d{1,2}):(?P<minute>\d{1,2})$', date_str)
	return datetime(
		# Eh oui, Parcoursup renvoie l'année sur 3 chiffres...
		year=int(date_match.group('annee')) + 2000,
		month=int(date_match.group('mois')),
		day=int(date_match.group('jour')),
		hour=int(date_match.group('heure')),
		minute=int(date_match.group('minute')),
		tzinfo=paris_tz,
	)

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
			'identifiant': {
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

class ParcoursupPersonne:
	SEXE_HOMME = Etudiant.SEXE_HOMME
	SEXE_FEMME = Etudiant.SEXE_FEMME

	def __init__(self, **kwargs):
		self.nom = kwargs.get('nom')
		self.prenom = kwargs.get('prenom')
		self.email = kwargs.get('email')
		self.adresse = kwargs.get('adresse')
		self.telephone_fixe = kwargs.get('telephone_fixe')
		self.telephone_mobile = kwargs.get('telephone_mobile')
		self.sexe = kwargs.get('sexe')

class ParcoursupCandidat(ParcoursupPersonne):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.code = kwargs.get('code')
		self.date_naissance = kwargs.get('date_naissance')
		self.ine = kwargs.get('ine')

	def to_json(self):
		return {
			'codeCandidat': int(self.code),
			'ine': str(self.ine),
			'nom': str(self.nom),
			'prenom': str(self.prenom),
			'dateNaissance': self.date_naissance.strftime('%d/%m/%Y')
		}

class ParcoursupResponsableLegal(ParcoursupPersonne):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.candidat = kwargs.get('candidat')

class ParcoursupProposition:
	ETAT_ATTENTE = 0
	ETAT_ACCEPTEE = 1
	ETAT_ACEPTEE_AUTRES_VOEUX = 2
	ETAT_REFUSEE = 3

	def __init__(self, **kwargs):
		self.session = kwargs.get('session')
		self.code_formation = kwargs.get('code_formation')
		self.code_etablissement = kwargs.get('code_etablissement')
		self.cesure = kwargs.get('cesure')
		self.internat = kwargs.get('internat')
		self.etat = kwargs.get('etat')
		self.date = kwargs.get('date')

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

	@staticmethod
	def formate_adresse(donnees):
		CODE_PAYS_FRANCE = '99100'
		code_pays = donnees.get('codepays', CODE_PAYS_FRANCE)
		if code_pays == CODE_PAYS_FRANCE:
			try:
				libelle_ville = Commune.objects.get(pk=donnees.get('codecommune')).libelle
			except Commune.DoesNotExist:
				libelle_ville = '**** COMMUNE INCONNUE ****'
				print("Commune {} inconnue".format(donnees.get('codecommune')))
			libelle_pays = ''
		else:
			libelle_ville = donnees.get('commune') or ''
			libelle_pays = donnees.get('libellepays') or ''

		raw_adresse = '{adresse1}\n{adresse2}\n{adresse3}\n{code_postal} {ville}\n{pays}'.format(
			adresse1=donnees.get('adresse1') or '',
			adresse2=donnees.get('adresse2') or '',
			adresse3=donnees.get('adresse3') or '',
			# Orthographie affligeante. On teste les deux, pour être
			# robuste à une future correction qui casse la
			# compatibilité.
			code_postal=donnees.get('codepostal', donnees.get('codepostale')) or '',
			ville=libelle_ville,
			pays=libelle_pays)
		return re.sub(r'\n+', '\n', raw_adresse).strip()

	def parse_parcoursup_admission(self, psup_json):
		"""
		Prend en paramètre le JSON envoyé par l'interface synchrone de
		Parcoursup et renvoie les informations structurées avec les
		classes ParcoursupCandidat, ParcoursupResponsableLegal et
		ParcoursupProposition.
		"""
		donnees = requests.utils.CaseInsensitiveDict(data=psup_json)
		candidat = ParcoursupCandidat(
			nom=donnees['nom'],
			prenom=donnees['prenom'],
			email=donnees['mail'],
			date_naissance=parse_french_date(donnees['dateNaissance']),
			code=donnees['codeCandidat'],
			ine=donnees['ine'],
			adresse=self.formate_adresse(donnees),
			telephone_fixe = donnees['telfixe'],
			telephone_mobile = donnees['telmobile'],
			sexe=ParcoursupCandidat.SEXE_HOMME if donnees['sexe'] == 'M'
				else ParcoursupCandidat.SEXE_FEMME,
		)

		proposition = ParcoursupProposition(
			code_formation=int(donnees['codeFormationPsup']),
			code_etablissement=donnees['codeEtablissementAffectation'],
			cesure=donnees['cesure'] == "1",
			internat=donnees['internat'] == "1",
			date=parse_date_reponse(donnees['dateReponse']),
			etat=int(donnees['codeSituation']),
		)

		responsables = []
		for i in (1, 2):
			try:
				responsables.append(ParcoursupResponsableLegal(
					nom=donnees['nomRL{}'.format(i)],
					prenom=donnees['prenomRL{}'.format(i)],
					email=donnees['mailRL{}'.format(i)],
					candidat=candidat))
			except KeyError:
				pass

		return {
			'candidat': candidat,
			'proposition': proposition,
			'responsables': responsables,
		}


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


def unsafe_auto_import_rest():
	psup = ParcoursupRest(
		login=settings.PARCOURSUP_REST_LOGIN,
		password=settings.PARCOURSUP_REST_PASSWORD,
		code_etablissement=settings.PARCOURSUP_UAI_ETABLISSEMENT,
	)
	req = psup.get_candidats_admis()
	candidats = []
	for psup_json in req.request.json():
		candidats.append(psup.parse_parcoursup_admission(psup_json))

	# Liste des codes Parcoursup des candidats admis
	codes_admis = []

	# Enregistrement des propositions en base de données
	for candidat in candidats:
		psup_etudiant = candidat['candidat']
		psup_prop = candidat['proposition']

		try:
			etudiant = Etudiant.objects.get(pk=psup_etudiant.code)
		except Etudiant.DoesNotExist:
			# On ignore les démissions
			if psup_prop.etat == ParcoursupProposition.ETAT_REFUSEE:
				continue

			# On importe l'étudiant qui n'existait pas encore
			etudiant = Etudiant(dossier_parcoursup=psup_etudiant.code)

		# On enregistre les coordonnées de l'étudiant, elles peuvent
		# avoir été mises à jour par rapport à ce qui était dans la base
		# de données.
		etudiant.nom = psup_etudiant.nom
		etudiant.prenom = psup_etudiant.prenom
		etudiant.email = psup_etudiant.email
		etudiant.adresse = psup_etudiant.adresse
		etudiant.telephone = psup_etudiant.telephone_fixe or ''
		etudiant.telephone_mobile = psup_etudiant.telephone_mobile or ''
		etudiant.sexe = psup_etudiant.sexe
		etudiant.date_naissance = psup_etudiant.date_naissance
		etudiant.save()

		# On enregistre la proposition faite à cet étudiant
		if psup_prop.etat != ParcoursupProposition.ETAT_REFUSEE:
			try:
				if psup_prop.etat == ParcoursupProposition.ETAT_ACCEPTEE:
					etat_prop = Proposition.ETAT_OUI
				elif psup_prop.etat == ParcoursupProposition.ETAT_ACCEPTEE_AUTRES_VOEUX:
					etat_prop = Proposition.ETAT_OUIMAIS
				else:
					continue

				proposition = Proposition(
					classe=Classe.objects.get(
						code_parcoursup=psup_prop.code_formation),
					etudiant=etudiant,
					date_proposition=psup_prop.date,
					internat=psup_prop.internat,
					cesure=psup_prop.cesure,
					etat=etat_prop)
				etudiant.nouvelle_proposition(proposition)
				codes_admis.append(etudiant.dossier_parcoursup)
			except Classe.DoesNotExist:
				pass
		else:
			etudiant.demission(psup_prop.date)

	# Les étudiants qui ne sont plus présents dans la liste des
	# candidats admis sont considérés comme démissionnaires.
	for etudiant in Etudiant.objects.exclude(
		dossier_parcoursup__in=codes_admis):
		etudiant.demission(timezone.now())

def auto_import_rest(mode=ParcoursupSynchro.MODE_MANUEL):
	# Sauvegarde de l'heure de début, pour l'historique
	date_debut = timezone.now()

	try:
	    unsafe_auto_import_rest()
	    resultat = ParcoursupSynchro.RESULTAT_OK
	except:
	    resultat = ParcoursupSynchro.RESULTAT_ERREUR

	date_fin = timezone.now()

	ParcoursupSynchro(date_debut=date_debut, date_fin=date_fin,
	        mode=mode, resultat=resultat,
			source=ParcoursupSynchro.SOURCE_REST).save()
