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
from dateutil.tz import gettz
import locale
import requests
import bs4

ParcoursupProposition = namedtuple('ParcoursupProposition', ('numero',
    'nom', 'prenom', 'etat', 'message', 'internat', 'date_reponse',
    'date_proposition', 'classe'))

ParcoursupColonne = namedtuple('ParcoursupColonne', ('nom', 'position',
    'parser',))

class Parcoursup:
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
        auth_data = {
                'g_ea_cod': user,
                'g_ea_mot_pas': password,
                'ACTION': 1,
                }
        self.session.post(self.purl('authentification'), auth_data)

    def disconnect(self):
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
        for (key, val) in Parcoursup.ETAT_CHOICES:
            if key == etat:
                return val

    def _url_classe_etat(self, classe, etat):
        etat_url = {Parcoursup.ETAT_OUI: 'prop_acc',
                Parcoursup.ETAT_OUIMAIS: 'prop_acc_att',
                Parcoursup.ETAT_DEMISSION: 'ref'}

        base_url = 'https://gestion.parcoursup.fr/Gestion/admissions.candidats.groupe?ACTION=1&cx_g_ta_cod={code_classe}&cx_g_ta_cod={code_classe}&cx_c_cg_cod={code_groupe}&liste={etat}'

        return base_url.format(code_classe=classe.code_parcoursup,
                code_groupe=classe.groupe_parcoursup,
                etat=etat_url[etat])

    def recupere_par_etat(self, classe, etat, candidats={}):
        html = self.session.get(self._url_classe_etat(classe, etat))
        soup = bs4.BeautifulSoup(html.text, 'lxml')
        table_candidats = soup.find('table', {'id': 'listeCandidats'})
        tbody = table_candidats.find('tbody')

        def parser_default(td):
            return td.contents[0].strip()

        def parser_nom(td):
            nom_parts = []
            for part in parser_default(td).split():
                if len(part) > 1 and part[1].isupper():
                    nom_parts.append(part)
            return ' '.join(nom_parts)

        def parser_prenom(td):
            prenom_parts = []
            for part in parser_default(td).split():
                if len(part) > 1 and part[1].islower():
                    prenom_parts.append(part)
            return ' '.join(prenom_parts)

        paris_tz = gettz('Europe/Paris')
        def parser_date_reponse(td):
            old_loc = locale.getlocale(locale.LC_TIME)
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
            date = datetime.datetime.strptime(parser_default(td),
                        "%d %b %Y %H:%M").replace(tzinfo=paris_tz)
            locale.setlocale(locale.LC_TIME, old_loc)
            return date

        def parser_date_proposition(td):
            old_loc = locale.getlocale(locale.LC_TIME)
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
            date = datetime.datetime.strptime(parser_default(td),
                        "%d %b").replace(year=datetime.date.today().year,
                                tzinfo=paris_tz)
            locale.setlocale(locale.LC_TIME, old_loc)
            return date

        colonnes_psup = ParcoursupProposition(
                numero=ParcoursupColonne('numero', 3,
                    lambda c: int(parser_default(c))),

                nom=ParcoursupColonne('nom', 4, parser_nom),

                prenom=ParcoursupColonne('prenom', 4, parser_prenom),

                message=ParcoursupColonne('message', 7, parser_default),

                etat=ParcoursupColonne('etat', 7, lambda _: etat),

                internat=ParcoursupColonne('internat', 9,
                    lambda td: parser_default(td) == "Avec internat"),

                date_reponse=ParcoursupColonne('date_reponse', 2, parser_date_reponse),

                date_proposition=ParcoursupColonne('date_proposition', 1,
                    parser_date_proposition),

                classe=ParcoursupColonne('classe', 0, lambda _: classe),
            )

        for tr in tbody.find_all('tr', recursive=False):
            tds = tr.find_all('td', recursive=False)

            candidat_props = []
            for field_name in ParcoursupProposition._fields:
                field = getattr(colonnes_psup, field_name)
                candidat_props.append(field.parser(tds[field.position]))

            candidat = ParcoursupProposition(*candidat_props)

            if candidat.numero not in candidats or \
                    candidats[candidat.numero].etat < candidat.etat:
                candidats[candidat.numero] = candidat

        return candidats

