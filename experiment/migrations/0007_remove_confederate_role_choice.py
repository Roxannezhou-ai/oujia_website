from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiment', '0006_update_postsurvey_help_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sessionmember',
            name='role',
            field=models.CharField(choices=[('R', 'Researcher'), ('P', 'Participant')], max_length=1),
        ),
    ]
