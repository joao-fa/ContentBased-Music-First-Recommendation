# Generated manually to drop obsolete recommendation telemetry columns

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0010_recommendationevaluation_primary_metric_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE api_recommendationevaluation
                    DROP COLUMN IF EXISTS base_metric;
                    ALTER TABLE api_recommendationbatch
                    DROP COLUMN IF EXISTS used_feature;
                    """,
                    reverse_sql="""
                    ALTER TABLE api_recommendationevaluation
                    ADD COLUMN IF NOT EXISTS base_metric varchar(100) NULL;
                    ALTER TABLE api_recommendationbatch
                    ADD COLUMN IF NOT EXISTS used_feature varchar(100) NULL;
                    """,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="recommendationbatch",
                    name="used_feature",
                ),
            ],
        ),
    ]
