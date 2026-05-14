# Generated manually for two-metric recommendation evaluation metadata

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0009_alter_recommendationevaluation_list_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="recommendationevaluation",
            name="primary_metric",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="recommendationevaluation",
            name="secondary_metric",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
