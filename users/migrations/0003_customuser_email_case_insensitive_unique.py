# Generated manually on 2026-06-04

from django.db import migrations, models
from django.db.models import Count
from django.db.models.functions import Lower


def normalize_existing_emails(apps, schema_editor):
    CustomUser = apps.get_model('users', 'CustomUser')
    duplicates = (
        CustomUser.objects
        .annotate(email_lower=Lower('email'))
        .values('email_lower')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    if duplicates.exists():
        duplicate_emails = ', '.join(item['email_lower'] for item in duplicates)
        raise RuntimeError(
            "Impossible d'ajouter l'unicité case-insensitive: "
            f"emails déjà en doublon: {duplicate_emails}"
        )

    for user in CustomUser.objects.all():
        normalized_email = user.email.lower()
        if user.email != normalized_email:
            user.email = normalized_email
            user.save(update_fields=['email'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_customuser_public_id'),
    ]

    operations = [
        migrations.RunPython(normalize_existing_emails, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='customuser',
            constraint=models.UniqueConstraint(
                Lower('email'),
                name='unique_customuser_email_ci',
            ),
        ),
    ]
