from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiment', '0010_alter_session_stage_demographicinfo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='demographicinfo',
            name='age',
        ),
        migrations.RemoveField(
            model_name='demographicinfo',
            name='gender',
        ),
        migrations.RemoveField(
            model_name='demographicinfo',
            name='ubc_student',
        ),
        migrations.AddField(
            model_name='demographicinfo',
            name='heard_ouija',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='demographicinfo',
            name='hsp_id',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
