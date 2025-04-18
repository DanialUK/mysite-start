# Generated by Django 5.1.7 on 2025-04-06 23:31

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("roles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="group",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="role",
                to="auth.group",
            ),
        ),
    ]
