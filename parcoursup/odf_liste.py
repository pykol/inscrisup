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
from odf.style import Style, TableColumnProperties
from odf.text import P

def par_classe(classes, fileout):
    ods = OpenDocumentSpreadsheet()

    style_civilite = Style(parent=ods.automaticstyles,
            name='col_civilite', family='table-column')
    TableColumnProperties(parent=style_civilite, columnwidth='1cm')

    style_nom = Style(parent=ods.automaticstyles,
            name='col_nom', family='table-column')
    TableColumnProperties(parent=style_nom, columnwidth='4cm')

    style_date = Style(parent=ods.automaticstyles,
            name='col_date', family='table-column')
    TableColumnProperties(parent=style_date, columnwidth='2.2cm')

    for classe in classes:
        table = Table(name=str(classe))
        table.addElement(TableColumn(stylename=style_civilite)) # Sexe
        table.addElement(TableColumn(stylename=style_nom)) # Nom
        table.addElement(TableColumn(stylename=style_nom)) # Prénom
        table.addElement(TableColumn(stylename=style_date)) # Date de naissance
        table.addElement(TableColumn()) # Internat
        table.addElement(TableColumn()) # État vœu

        # En-tête de la feuille
        tr = TableRow()
        cell = TableCell(numbercolumnsspanned=6)
        cell.addElement(P(text=str(classe)))
        tr.addElement(cell)
        table.addElement(tr)

        for etudiant in classe.admissions().order_by('nom'):
            tr = TableRow()
            table.addElement(tr)

            cell = TableCell()
            cell.addElement(P(text=etudiant.get_sexe_display()))
            tr.addElement(cell)

            cell = TableCell()
            cell.addElement(P(text=etudiant.nom))
            tr.addElement(cell)

            cell = TableCell()
            cell.addElement(P(text=etudiant.prenom))
            tr.addElement(cell)

            cell = TableCell(valuetype='date',
                    datevalue=str(etudiant.date_naissance))
            cell.addElement(P(text=etudiant.date_naissance))
            tr.addElement(cell)

            cell = TableCell()
            if etudiant.proposition_actuelle.internat:
                cell.addElement(P(text="Interne"))
            tr.addElement(cell)

            cell = TableCell()
            cell.addElement(P(text=etudiant.proposition_actuelle.get_statut_display()))
            tr.addElement(cell)

        ods.spreadsheet.addElement(table)

    ods.write(fileout)
