# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-25 12:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parcoursup', '0010_etudiant_adresse'),
    ]

    operations = [
        migrations.AddField(
            model_name='classe',
            name='groupe_parcoursup',
            field=models.SmallIntegerField(default=-1),
            preserve_default=False,
        ),
    ]