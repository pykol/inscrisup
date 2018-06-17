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

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableColumn, TableRow, TableCell
from odf.text import P

def par_classe(classes, fileout):
    ods = OpenDocumentSpreadsheet()
    for classe in classes:
        table = Table(name=str(classe))
        table.addElement(TableColumn())
        table.addElement(TableColumn())
        table.addElement(TableColumn())

        for etudiant in classe.admissions().order_by('nom'):
            tr = TableRow()
            table.addElement(tr)

            cell = TableCell()
            cell.addElement(P(text=str(etudiant)))
            tr.addElement(cell)

            cell = TableCell()
            cell.addElement(P(text=etudiant.date_naissance))
            tr.addElement(cell)

            cell = TableCell()
            cell.addElement(P(text=etudiant.proposition_actuelle.get_statut_display()))
            tr.addElement(cell)

        ods.spreadsheet.addElement(table)

    ods.write(fileout)
