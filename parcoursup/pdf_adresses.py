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

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

def pdf_adresses(etudiants, fileout):
	c = canvas.Canvas(fileout)
	pos_left = 11.5 * cm
	pos_bottom = 25.3 * cm
	interligne = 0.6 * cm
	for etudiant in etudiants:
		c.drawString(pos_left, pos_bottom, etudiant.civilite() + " " + str(etudiant))
		bot_actuel = pos_bottom - interligne
		lignes_adresse = str(etudiant.adresse).split("\n")
		for ligne in lignes_adresse:
			c.drawString(pos_left, bot_actuel, ligne.strip())
			bot_actuel -= interligne
		c.showPage()
	c.save()

def pdf_etiquettes_adresses(etudiants, fileout):
	NB_LIGNES = 7
	NB_COLONNES = 2

	c = canvas.Canvas(fileout)
	# Marge du bas diminuée pour décaler un peu les étiquettes vers
	# le bas.
	margin_bottom = 1.61 * cm - 0.4 * cm
	# Marge de gauche augmentée pour décaler un peu les étiquettes vers
	# la droite.
	margin_left = 0.51 * cm + 0.5 * cm
	gutter = 0.2 * cm
	etiq_width = 9.91 * cm
	etiq_height = 3.81 * cm
	interligne = 0.6 * cm

	for pos_etudiant, etudiant in enumerate(etudiants):
		pos_page = pos_etudiant % (NB_LIGNES * NB_COLONNES)

		if pos_etudiant > 0 and pos_page == 0:
			c.showPage()


		# On détermine la position sur l'étiquette
		pos_left = margin_left + (pos_page % NB_COLONNES) * (etiq_width + gutter)
		pos_bottom = margin_bottom + (NB_LIGNES - pos_page //
				NB_COLONNES) * etiq_height - interligne

		c.drawString(pos_left, pos_bottom, etudiant.civilite() + " " + str(etudiant))
		bot_actuel = pos_bottom - interligne
		lignes_adresse = str(etudiant.adresse).split("\n")
		for ligne in lignes_adresse:
			c.drawString(pos_left, bot_actuel, ligne.strip())
			bot_actuel -= interligne
	c.save()
