from django.conf import settings
from django.db import migrations


def configure_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.update_or_create(
        id=1,
        defaults={"domain": settings.SITE_DOMAIN, "name": settings.SITE_NAME},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("sites", "0001_initial"),
        ("registry", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(configure_site, migrations.RunPython.noop),
    ]
