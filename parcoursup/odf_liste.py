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
from odf.style import Style, TableColumnProperties, TextProperties
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

    style_titre = Style(parent=ods.styles,
            name='ligne_titre', family='paragraph')
    TextProperties(parent=style_titre, fontweight='bold',
            fontsize='14pt')

    style_entete = Style(parent=ods.styles,
            name='cell_entete', family='paragraph')
    TextProperties(parent=style_entete, fontweight='bold')

    for classe in classes:
        table = Table(name=str(classe))
        table.addElement(TableColumn(stylename=style_civilite)) # Sexe
        table.addElement(TableColumn(stylename=style_nom)) # Nom
        table.addElement(TableColumn(stylename=style_nom)) # Prénom
        table.addElement(TableColumn(stylename=style_date)) # Date de naissance
        table.addElement(TableColumn()) # Internat
        table.addElement(TableColumn()) # État vœu

        # En-tête de la feuille
        tr = TableRow(parent=table)
        cell = TableCell(parent=tr, numbercolumnsspanned=6)
        cell.addElement(P(text=str(classe), stylename=style_titre))

        tr = TableRow(parent=table)
        TableCell(parent=tr) # Sexe
        P(parent=TableCell(parent=tr), text="Nom", stylename=style_entete)
        P(parent=TableCell(parent=tr), text="Prénom", stylename=style_entete)
        P(parent=TableCell(parent=tr), text="Date de naissance", stylename=style_entete)
        P(parent=TableCell(parent=tr), text="Internat", stylename=style_entete)
        P(parent=TableCell(parent=tr), text="État Parcoursup", stylename=style_entete)

        for etudiant in classe.admissions().order_by('nom'):
            tr = TableRow()
            table.addElement(tr)

            TableCell(parent=tr).addElement(P(text=etudiant.get_sexe_display()))

            TableCell(parent=tr).addElement(P(text=etudiant.nom))

            TableCell(parent=tr).addElement(P(text=etudiant.prenom))

            cell = TableCell(valuetype='date',
                    datevalue=str(etudiant.date_naissance))
            cell.addElement(P(text=etudiant.date_naissance))
            tr.addElement(cell)

            cell = TableCell()
            if etudiant.proposition_actuelle.internat:
                cell.addElement(P(text="Interne"))
            tr.addElement(cell)

            TableCell(parent=tr).addElement(P(text=etudiant.proposition_actuelle.get_statut_display()))

        ods.spreadsheet.addElement(table)

    ods.write(fileout)
