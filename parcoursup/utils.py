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

import datetime
import re
from dateutil.tz import gettz

date_re = re.compile(r'(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})$')
def parse_date(date):
	"""
	Renvoie un objet datetime.date à partir d'une chaine au format
	JJ/MM/AAAA.
	"""
	match = date_re.match(date)
	if match:
		kw = {k: int(v) for k, v in match.groupdict().items()}
	return datetime.date(**kw)

def format_adresse_pays(**parts):
	default_france = "{adresse1}\n{adresse2}\n{code_postal} {ville}"
	autre = "{adresse1}\n{adresse2}\n{code_postal}\n{ville}\n{pays}"

	if parts.get('pays', 'FR') in ('', 'FR'):
		res = default_france.format(**parts)
	else:
		res = autre.format(**parts)
	return re.sub(r'\n+', '\n', res)

def parse_datetime(date):
	"""
	Renvoie un objet datetime.datetime à partir d'une chaine au format
	"JJ/MM/AAAA HH:MM". Le fuseau horaire est fixé comme étant celui de
	Paris.

	Franchement, Parcoursup, vous devriez savoir qu'il existe une norme
	ISO pour les dates et heures, cela nous éviterait toutes ces
	bizarreries.
	"""
	paris_tz = gettz('Europe/Paris')
	return datetime.datetime.strptime(date, "%d/%m/%Y %H:%M").replace(tzinfo=paris_tz)
