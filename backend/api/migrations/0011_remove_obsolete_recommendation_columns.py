# Generated manually to drop obsolete recommendation telemetry columns

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0010_recommendationevaluation_primary_metric_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="recommendationevaluation",
            name="base_metric",
        ),
        migrations.RemoveField(
            model_name="recommendationbatch",
            name="used_feature",
        ),
    ]
