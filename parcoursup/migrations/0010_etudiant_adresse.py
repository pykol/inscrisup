# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-25 11:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parcoursup', '0009_classe_code_parcoursup'),
    ]

    operations = [
        migrations.AddField(
            model_name='etudiant',
            name='adresse',
            field=models.TextField(blank=True),
        ),
    ]
