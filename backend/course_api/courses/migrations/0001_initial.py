# Generated by Django 5.1.4 on 2024-12-22 17:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("course_code", models.CharField(max_length=20, unique=True)),
                ("course_prefix", models.CharField(max_length=10)),
                ("course_number", models.CharField(max_length=10)),
                ("course_name", models.CharField(max_length=255)),
                (
                    "course_delivery_type",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                ("prereqs", models.TextField(blank=True, null=True)),
                ("hours", models.CharField(blank=True, max_length=20, null=True)),
                ("fees", models.CharField(blank=True, max_length=50, null=True)),
                ("course_description", models.TextField(blank=True, null=True)),
                ("course_link", models.URLField(blank=True, max_length=500, null=True)),
            ],
            options={
                "ordering": ["course_prefix", "course_number"],
            },
        ),
        migrations.CreateModel(
            name="Schedule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("day_of_week", models.CharField(max_length=50)),
                ("start_time", models.TimeField(blank=True, null=True)),
                ("end_time", models.TimeField(blank=True, null=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="schedules",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "ordering": ["start_date", "start_time"],
            },
        ),
    ]
