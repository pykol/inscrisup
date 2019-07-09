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
from odf.table import Table, TableColumn, TableRow, TableCell, \
		CoveredTableCell
from odf.style import Style, TableColumnProperties, TableRowProperties, \
		TextProperties, ParagraphProperties
import odf.number
from odf.text import P

from parcoursup.models import Etudiant

def par_classe(classes, fileout):
	ods = OpenDocumentSpreadsheet()

	style_civilite = Style(parent=ods.automaticstyles,
			name='col_civilite', family='table-column')
	TableColumnProperties(parent=style_civilite, columnwidth='1cm')

	style_nom = Style(parent=ods.automaticstyles,
			name='col_nom', family='table-column')
	TableColumnProperties(parent=style_nom, columnwidth='4.5cm')

	style_date = Style(parent=ods.automaticstyles,
			name='col_date', family='table-column')
	TableColumnProperties(parent=style_date, columnwidth='3.2cm')

	style_internat = Style(parent=ods.automaticstyles,
			name='col_internat', family='table-column')
	TableColumnProperties(parent=style_internat, columnwidth='3.2cm')

	style_classe = Style(parent=ods.automaticstyles,
			name='col_classe', family='table-column')
	TableColumnProperties(parent=style_classe, columnwidth='3.2cm')

	style_etat_voeu = Style(parent=ods.automaticstyles,
			name='col_etat_voeu', family='table-column')
	TableColumnProperties(parent=style_etat_voeu, columnwidth='4cm')

	style_titre = Style(parent=ods.automaticstyles,
			name='cell_titre', family='table-cell')
	TextProperties(parent=style_titre, fontweight='bold',
			fontsize='14pt')
	ParagraphProperties(parent=style_titre, textalign='center')

	style_ligne_titre = Style(parent=ods.automaticstyles,
			name='ligne_titre', family='table-row')
	TableRowProperties(parent=style_ligne_titre, rowheight='8mm')

	style_entete = Style(parent=ods.automaticstyles,
			name='cell_entete', family='table-cell')
	TextProperties(parent=style_entete, fontweight='bold')

	number_style_date_format = odf.number.DateStyle(parent=ods.automaticstyles,
			name='date_number')
	odf.number.Day(parent=number_style_date_format, style='long')
	odf.number.Text(parent=number_style_date_format, text="/")
	odf.number.Month(parent=number_style_date_format, style='long')
	odf.number.Text(parent=number_style_date_format, text="/")
	odf.number.Year(parent=number_style_date_format, style='long')
	style_date_format = Style(parent=ods.automaticstyles,
			name='cell_date', family='table-cell',
			datastylename=number_style_date_format)

	for classe in classes:
		table = Table(name=str(classe))
		table.addElement(TableColumn(stylename=style_civilite)) # Sexe
		table.addElement(TableColumn(stylename=style_nom)) # Nom
		table.addElement(TableColumn(stylename=style_nom)) # Prénom
		table.addElement(TableColumn(stylename=style_date)) # Date de naissance
		table.addElement(TableColumn(stylename=style_internat)) # Internat
		table.addElement(TableColumn(stylename=style_etat_voeu)) # État vœu
		table.addElement(TableColumn(stylename=style_nom)) # E-mail
		table.addElement(TableColumn(stylename=style_nom)) # Téléphone
		table.addElement(TableColumn(stylename=style_nom)) # Mobile

		# En-tête de la feuille
		tr = TableRow(parent=table, stylename=style_ligne_titre)
		cell = TableCell(parent=tr,
				numbercolumnsspanned=9, numberrowsspanned=1,
				valuetype='string', stylename=style_titre)
		cell.addElement(P(text=str(classe)))
		CoveredTableCell(parent=tr, numbercolumnsrepeated=8)

		tr = TableRow(parent=table)
		TableCell(parent=tr) # Sexe
		P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Nom")
		P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Prénom")
		P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Date de naissance")
		P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Internat")
		P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="État Parcoursup")
		P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="E-mail")
		P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Téléphone")
		P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Mobile")

		for etudiant in classe.admissions().order_by('nom'):
			tr = TableRow()
			table.addElement(tr)

			TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.get_sexe_display()))

			TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.nom))

			TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.prenom))

			cell = TableCell(valuetype='date',
					datevalue=str(etudiant.date_naissance),
					stylename=style_date_format)
			cell.addElement(P(text=etudiant.date_naissance))
			tr.addElement(cell)

			cell = TableCell(valuetype='string')
			if etudiant.proposition_actuelle.internat:
				cell.addElement(P(text="Interne"))
			tr.addElement(cell)

			TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.proposition_actuelle.get_etat_display()))

			TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.email))
			TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.telephone))
			TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.telephone_mobile))

		ods.spreadsheet.addElement(table)

	# Liste générale pour l'infirmerie
	table = Table(name="Infirmerie")
	ods.spreadsheet.addElement(table)
	table.addElement(TableColumn(stylename=style_civilite)) # Sexe
	table.addElement(TableColumn(stylename=style_nom)) # Nom
	table.addElement(TableColumn(stylename=style_nom)) # Prénom
	table.addElement(TableColumn(stylename=style_classe)) # Classe
	table.addElement(TableColumn(stylename=style_date)) # Date de naissance
	table.addElement(TableColumn(stylename=style_internat)) # Internat

	# En-tête de la feuille
	tr = TableRow(parent=table, stylename=style_ligne_titre)
	cell = TableCell(parent=tr,
			numbercolumnsspanned=9, numberrowsspanned=1,
			valuetype='string', stylename=style_titre)
	cell.addElement(P(text="Liste de tous les étudiants admis"))
	tr = TableRow(parent=table)
	TableCell(parent=tr) # Sexe
	P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Nom")
	P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Prénom")
	P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Classe")
	P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Date de naissance")
	P(parent=TableCell(parent=tr, valuetype='string', stylename=style_entete), text="Internat")

	for etudiant in Etudiant.objects.filter(
		proposition_actuelle__isnull=False,
		proposition_actuelle__date_demission__isnull=True
		).order_by('nom', 'prenom'):

		tr = TableRow(parent=table)

		TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.get_sexe_display()))

		TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.nom))

		TableCell(parent=tr, valuetype='string').addElement(P(text=etudiant.prenom))

		TableCell(parent=tr,
			valuetype='string').addElement(P(text=str(etudiant.proposition_actuelle.classe)))

		cell = TableCell(valuetype='date',
				datevalue=str(etudiant.date_naissance),
				stylename=style_date_format)
		cell.addElement(P(text=etudiant.date_naissance))
		tr.addElement(cell)

		cell = TableCell(valuetype='string')
		if etudiant.proposition_actuelle.internat:
			cell.addElement(P(text="Interne"))
		tr.addElement(cell)


	ods.write(fileout)
