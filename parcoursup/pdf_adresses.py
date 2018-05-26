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

def pdf_adresses(actions, fileout):
    c = canvas.Canvas(fileout)
    pos_left = 11 * cm
    pos_bottom = 24 * cm
    interligne = 0.7 * cm
    for action in actions:
        etudiant = action.proposition.etudiant
        c.drawString(pos_left, pos_bottom, str(etudiant))
        bot_actuel = pos_bottom - interligne
        lignes_adresse = str(etudiant.adresse).split("\n")
        for ligne in lignes_adresse:
            c.drawString(pos_left, bot_actuel, ligne.strip())
            bot_actuel -= interligne
        c.showPage()
    c.save()
