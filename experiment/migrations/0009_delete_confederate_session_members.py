from django.db import migrations


def delete_confederate_members(apps, schema_editor):
    SessionMember = apps.get_model('experiment', 'SessionMember')
    SessionMember.objects.filter(role='C').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('experiment', '0008_alter_session_stage'),
    ]

    operations = [
        migrations.RunPython(delete_confederate_members, migrations.RunPython.noop),
    ]
