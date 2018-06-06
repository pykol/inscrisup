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

from collections import namedtuple
import datetime
import locale
import tempfile
import re
import csv
import os

from django.conf import settings
from dateutil.tz import gettz
import requests
import bs4

from .models import Etudiant, Proposition, Classe

ParcoursupProposition = namedtuple('ParcoursupProposition', ('numero',
    'nom', 'prenom', 'etat', 'message', 'internat', 'date_reponse',
    'date_proposition', 'classe'))

ParcoursupColonne = namedtuple('ParcoursupColonne', ('nom', 'libelle', 'position',
    'parser',))

class Parcoursup:
    """
    Classe qui fournit des méthodes d'extraction des données de Parcoursup.

    Cette classe utilise les modules requests et BeautifulSoup4 pour se
    connecter au site web de Parcoursup, analyser les pages HTML du
    site, et extraire les informations qui nous intéressent.

    On utilise un compte dédié créé sur Parcoursup par l'administration
    du lycée.
    """
    def __init__(self):
        self.session = requests.Session()

    def purl(self, fin):
        return 'https://gestion.parcoursup.fr/Gestion/%s' % (fin,)

    def dget(self, url, *args, **kwargs):
        full_url = self.purl(url)
        r = self.session.get(full_url, *args, **kwargs)
        # print('%s: %d' % (full_url, r.status_code))
        return r

    def connect(self, user, password):
        """
        Identification sur Parcoursup

        Cette méthode doit être appelée avant toute autre.
        """
        auth_data = {
                'g_ea_cod': user,
                'g_ea_mot_pas': password,
                'ACTION': 1,
                }
        self.session.post(self.purl('authentification'), auth_data)

    def disconnect(self):
        """
        Déconnexion de Parcoursup

        Cette méthode ferme la session qui a été ouverte plus tôt lors
        d'un appel à la méthode connect.
        """
        self.dget('authentification?ACTION=2&sId=' + self.session.cookies.get('JSESSIONID'))

    # Prendre impérativement les mêmes valeurs que dans le modèle
    # Etudiant.
    ETAT_OUI = 0
    ETAT_OUIMAIS = 1
    ETAT_DEMISSION = -1

    ETAT_CHOICES = (
            (ETAT_OUI, 'oui'),
            (ETAT_OUIMAIS, 'oui-mais'),
            (ETAT_DEMISSION, 'demission'),
        )

    def get_etat_display(self, etat):
        """
        Retourne la chaine de caractères associé, dans la liste
        ETAT_CHOICES, à la valeur numérique de l'état donné en
        paramètre.
        """
        for (key, val) in Parcoursup.ETAT_CHOICES:
            if key == etat:
                return val

    def _url_classe_etat(self, classe, etat):
        """
        Étant donné une classe et l'état des candidats à rechercher,
        cette fonction renvoie l'adresse de la page Parcoursup où
        trouver ces candidats.
        """
        etat_url = {Parcoursup.ETAT_OUI: 'prop_acc',
                Parcoursup.ETAT_OUIMAIS: 'prop_acc_att',
                Parcoursup.ETAT_DEMISSION: 'ref'}

        base_url = 'https://gestion.parcoursup.fr/Gestion/admissions.candidats.groupe?ACTION=1&cx_g_ta_cod={code_classe}&cx_g_ta_cod={code_classe}&cx_c_cg_cod={code_groupe}&liste={etat}'

        return base_url.format(code_classe=classe.code_parcoursup,
                code_groupe=classe.groupe_parcoursup,
                etat=etat_url[etat])

    def _trouve_colonnes(self, table_candidats, colonnes):
        """
        Détermine, sur une page donnée, les positions des colonnes à
        partir de leurs libellés.

        La méthode recupere_par_etat recherche ses informations dans les
        différentes colonnes du tableau renvoyé par Parcoursup. Elle a
        besoin pour cela de savoir dans quelle colonne se trouve quelle
        information. Elle dispose pour cela de numéros de colonnes
        (valeurs par défaut codées en dur). Cependant, Parcoursup ne
        renvoie pas toujours les mêmes colonnes selon les situations
        (par exemple, l'ordre d'appel est parfois affiché, parfois non).

        Cette fonction regarde l'en-tête du tableau Parcoursup pour
        déterminer, d'après les libellés, les positions des colonnes qui
        nous intéressent.

        Le paramètre table_candidats doit contenir le tableau des
        candidats extrait de la page Parcoursup.

        Le paramètre colonnes est un dictionnaire qui à chaque
        identifiant de colonne associe une ParcoursupColonne. Le champ
        position de cette ParcoursupColonne sera mis à jour si on trouve
        le libellé correspondant.

        La méthode renvoie un nouveau dictionnaire suivant le même
        format, mais avec les positions mises à jour.
        """
        # On commence par extraire la liste de tous les libellés
        # présents dans le tableau, que l'on stocke dans un dictionnaire
        # qui à chaque libellé associe sa position.
        thead = table_candidats.find('thead')
        positions = {}
        for index, th in enumerate(thead.find_all('th')):
            if th.string:
                positions[th.string.strip()] = index

        # On met ensuite à jour les positions des colonnes données en
        # paramètre lorsque l'on trouve le libellé correspondant.
        res = {}
        for col in colonnes:
            colonne = colonnes[col]
            if colonne.libelle and colonne.libelle in positions:
                colonne = colonne._replace(position=positions[colonne.libelle])
            res[col] = colonne

        return res

    def recupere_par_etat(self, classe, etat, candidats={}):
        """
        Méthode qui récupère la liste des candidatures pour la classe
        et l'état (égal à l'une des constantes ETAT_xxx) donnés en
        paramètres.

        Elle renvoie un dictionnaire qui à chaque numéro de candidat
        associe une ParcoursupProposition construite à parties des
        données Parcoursup.

        Elle accepte un paramètre facultatif candidats, qui est un
        dictionnaire qui contient déjà des propositions pour des
        candidats. Dans ce cas, ce dictionnaire est modifié en ajoutant
        les nouvelles propositions et est renvoyé à la fin de l'appel.
        Seule la proposition avec le meilleur état est conservée pour
        chaque candidat (un oui définitif est meilleur qu'un oui avec
        attente, qui est meilleur qu'une démission).
        """
        html = self.session.get(self._url_classe_etat(classe, etat))
        soup = bs4.BeautifulSoup(html.text, 'html.parser')
        table_candidats = soup.find('table', {'id': 'listeCandidats'})
        tbody = table_candidats.find('tbody')

        # Chaque entrée du tableau Parcoursup est une balise HTML <td>. On
        # se donne un jeu de parsers qui convertissent, selon le type de
        # colonne que l'on attend, le contenu de la balise (qui est une
        # chaine de caractères) en un type Python.

        def parser_default(td):
            """
            Parser par défaut qui renvoie simplement le texte de la
            colonne, auquel on retire les caractères d'espacement
            parasites au début et à la fin.
            """
            return td.contents[0].strip()

        def parser_nom(td):
            """
            Parcoursup met dans la même colonne le nom et le prénom de
            chaque candidat. Ce parser extrait le nom de famille en
            utilisant le fait que Parcoursup le met entièrement en
            majuscules.
            """
            nom_parts = []
            for part in parser_default(td).split():
                # En fait, on regarde uniquement si la deuxième lettre
                # du mot est une majuscule.
                if len(part) > 1 and part[1].isupper():
                    nom_parts.append(part)
            return ' '.join(nom_parts)

        def parser_prenom(td):
            """
            Parcoursup met dans la même colonne le nom et le prénom de
            chaque candidat. Ce parser extrait le prénom utilisant le
            fait que Parcoursup met uniquement la première lettre du
            prénom en majuscule.
            """
            prenom_parts = []
            for part in parser_default(td).split():
                # On teste en fait uniquement si la deuxième lettre est
                # une minuscule.
                if len(part) > 1 and part[1].islower():
                    prenom_parts.append(part)
            return ' '.join(prenom_parts)

        # Une date et heure est ambigüe si elle n'est pas stockée avec
        # l'indication du fuseau horaire correspondant. Les heures de
        # Parcoursup sont à l'heure légale française. On prépare le
        # fuseau horaire pour l'attacher ensuite aux heures que l'on
        # récupèrera sur le site web.
        paris_tz = gettz('Europe/Paris')

        def parser_date_reponse(td):
            """
            Transformation du texte donnant la date de réponse en un
            objet datetime.datetime Python.
            """
            # La fonction strptime() interprète le motif "%b" comme
            # étant le nom du mois en toutes lettres. Elle doit pour
            # cela savoir dans quelle langue on travaille. On force
            # temporairement le changement de locale pour travailler en
            # français.
            old_loc = locale.getlocale(locale.LC_TIME)
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
            try:
                date = datetime.datetime.strptime(parser_default(td),
                        "%d %b %Y %H:%M").replace(tzinfo=paris_tz)
            except ValueError:
                date = None
            # On remet la locale à son ancienne valeur pour ne pas
            # risquer de perturber le reste du monde.
            locale.setlocale(locale.LC_TIME, old_loc)
            return date

        def parser_date_proposition(td):
            """
            Transformation du texte donnant la date de proposition en un
            objet datetime.datetime Python.

            Parcoursup utilise de temps à autre deux formats différents
            pour cette colonne, soit en indiquant uniquement le jour et
            le mois, soit en indiquant la date complète avec l'heure.

            On tente les deux formats. Quand il s'agit du premier,
            Parcoursup ne précise ni l'heure de proposition, ni l'année.
            On choisit minuit pour l'heure, et l'année en cours au
            moment de l'exécution de la méthode.
            """
            # La fonction strptime() interprète le motif "%b" comme
            # étant le nom du mois en toutes lettres. Elle doit pour
            # cela savoir dans quelle langue on travaille. On force
            # temporairement le changement de locale pour travailler en
            # français.
            old_loc = locale.getlocale(locale.LC_TIME)
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
            try:
                date = datetime.datetime.strptime(parser_default(td),
                        "%d %b").replace(year=datetime.date.today().year,
                                tzinfo=paris_tz)
            except ValueError:
                date = parser_date_reponse(td)
            # On remet la locale à son ancienne valeur pour ne pas
            # risquer de perturber le reste du monde.
            locale.setlocale(locale.LC_TIME, old_loc)
            return date

        # Liste des colonnes que l'on va rechercher pour chaque
        # candidat. Les positions indiquées en dur correspondent à ce
        # que je vois quand j'ouvre les pages avec mon navigateur, mais
        # pas toujours à ce que Parcoursup renvoie lorsque l'on ouvre la
        # page avec cette classe. La méthode _trouve_colonnes se charge
        # donc de mettre à jour les positions en fonction des libellés.
        colonnes_psup = self._trouve_colonnes(table_candidats, {
                'numero': ParcoursupColonne('numero', 'N° dossier', 3,
                    lambda c: int(parser_default(c))),

                'nom': ParcoursupColonne('nom', 'Nom et prénom', 4, parser_nom),

                'prenom': ParcoursupColonne('prenom', 'Nom et prénom', 4, parser_prenom),

                'message': ParcoursupColonne('message', 'Etat', 7, parser_default),

                'etat': ParcoursupColonne('etat', 'Etat', 7, lambda _: etat),

                'internat': ParcoursupColonne('internat', 'Internat', 9,
                    lambda td: parser_default(td) == "Avec internat"),

                'date_reponse': ParcoursupColonne('date_reponse',
                    'Date de la réponse', 2, parser_date_reponse),

                'date_proposition': ParcoursupColonne('date_proposition',
                    'Date de la proposition', 1, parser_date_proposition),

                'classe': ParcoursupColonne('classe', None, 0, lambda _: classe),
            })

        # Mise à jour du dictionnaire des candidats avec toutes les
        # propositions trouvées sur la page. Chaque proposition est dans
        # une balise <tr>. Cependant, Parcoursup produit du code HTML
        # comme il y a plus de 20 ans, et imbrique des tableaux dans des
        # tableaux. L'argument "recursive=False" permet de n'attraper
        # que les lignes du tableau actuel, pas les lignes des tableaux
        # imbriqués plus profondément...
        for tr in tbody.find_all('tr', recursive=False):
            tds = tr.find_all('td', recursive=False)

            candidat_props = []
            for field_name in ParcoursupProposition._fields:
                field = colonnes_psup[field_name]
                candidat_props.append(field.parser(tds[field.position]))

            candidat = ParcoursupProposition(*candidat_props)

            if candidat.numero not in candidats or \
                    candidats[candidat.numero].etat < candidat.etat:
                candidats[candidat.numero] = candidat

        return candidats

    def fichier_admissions(self, classe):
        """
        Téléchargement du fichier d'admissions pour extraire les
        adresses e-mail et postale.
        """
        base_url = 'https://gestion.parcoursup.fr/Gestion/admissions.fichiers?ACTION=19&cf_g_ta_cod={code_classe}&cf_g_ti_cod={code_classe}&cf_g_ti_flg_int=0&cf_g_ea_cod_aff={code_etablissement}&cf_g_ea_cod_ins={code_etablissement}'
        url = base_url.format(code_classe=classe.code_parcoursup,
                code_etablissement='0740003B')
        csv_resp = self.session.get(url, stream=True)

        csv_temp = tempfile.TemporaryFile(mode='r+b')
        for chunk in csv_resp.iter_content(chunk_size=128):
            csv_temp.write(chunk)

        # Après l'écriture, csv_temp est placé à la fin du fichier. On
        # se remet au début pour lire.
        csv_temp.seek(0)
        csv_temp_text = open(csv_temp.fileno(), 'rt', encoding='utf-8')
        csv_file = csv.reader(csv_temp_text, delimiter=';')

        adresses = {}

        # On ignore la première ligne qui contient uniquement les
        # en-têtes
        next(csv_file)

        # On traite les adresses de chaque étudiant
        date_re = re.compile(r'(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})$')
        def parse_date(date):
            match = date_re.match(date)
            if match:
                kw = {k: int(v) for k, v in match.groupdict().items()}
                return datetime.date(**kw)

        def format_adresse_pays(**parts):
            default_france = "{adresse1}\n{adresse2}\n{code_postal} {ville}\n{pays}"
            autre = "{adresse1}\n{adresse2}\n{code_postal}\n{ville}\n{pays}"

            res = ""
            if 'pays' in parts and parts['pays'] == "":
                res = default_france.format(**parts)
            else:
                res = autre.format(**parts)
            return re.sub(r'\n+', '\n', res)

        for ligne in csv_file:
            numero = int(ligne[0])

            adresse = format_adresse_pays(
                    adresse1 = ligne[6],
                    adresse2 = ligne[7],
                    code_postal = ligne[8],
                    ville = ligne[9],
                    pays = ligne[10])

            email = ligne[21]

            if ligne[2] == 'M.':
                sexe = Etudiant.SEXE_HOMME
            else:
                sexe = Etudiant.SEXE_FEMME

            date_naissance = parse_date(ligne[5])

            adresses[numero] = {'adresse': adresse, 'email': email,
                    'sexe': sexe, 'date_naissance': date_naissance}

        return adresses

def auto_import():
    psup = Parcoursup()
    psup.connect(settings.PARCOURSUP_USER, settings.PARCOURSUP_PASS)

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
