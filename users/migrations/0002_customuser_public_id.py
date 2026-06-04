# Generated manually on 2026-06-04

import uuid

from django.db import migrations, models


def populate_public_ids(apps, schema_editor):
    CustomUser = apps.get_model('users', 'CustomUser')
    for user in CustomUser.objects.filter(public_id__isnull=True):
        user.public_id = uuid.uuid4()
        user.save(update_fields=['public_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='public_id',
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='customuser',
            name='public_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
