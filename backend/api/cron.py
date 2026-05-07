from django.core.management import call_command


def export_recurring_database_snapshots():
    """Export recommendation snapshots from cron."""
    call_command("export_database_to_drive", profile="recurring")


def export_startup_database_snapshots():
    """Export static startup snapshots for tracks and cluster metadata."""
    call_command("export_database_to_drive", profile="startup")
