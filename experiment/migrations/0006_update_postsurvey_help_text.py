from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiment', '0005_predictionresponse'),
    ]

    operations = [
        migrations.AlterField(
            model_name='postsurvey',
            name='believe_supernatural',
            field=models.IntegerField(help_text='How believable did the prediction system feel? (1-7)'),
        ),
        migrations.AlterField(
            model_name='postsurvey',
            name='felt_control',
            field=models.IntegerField(help_text='How much control did you feel over your responses? (1-7)'),
        ),
        migrations.AlterField(
            model_name='postsurvey',
            name='felt_presence',
            field=models.IntegerField(help_text='Did you feel the prediction system influenced your responses? (1-7)'),
        ),
    ]
