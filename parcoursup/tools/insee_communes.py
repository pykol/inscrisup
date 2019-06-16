#!env python
# -*- coding: utf-8 -*-

"""
Transforme le fichier des communes de l'INSEE au format dBase en
instantané Django au format JSON.
"""

import sys
import json
import dbf

table_communes = dbf.Table(sys.argv[1], codepage='cp1252').open()
res = []
for commune in table_communes:
	res.append({
		'model': 'parcoursup.commune',
		'pk': commune.com,
		'fields': {
			'libelle': commune.libelle.strip(),
			}
		})

print(json.dumps(res))
