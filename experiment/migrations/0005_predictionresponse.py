from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('experiment', '0004_session_verbal_play_nonce_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PredictionResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.CharField(choices=[('Y', 'Yes'), ('N', 'No')], max_length=1)),
                ('confidence', models.CharField(choices=[('G', 'Guess'), ('S', 'Sure')], max_length=1)),
                ('reaction_time_ms', models.PositiveIntegerField()),
                ('predicted_answer', models.CharField(choices=[('Y', 'Yes'), ('N', 'No')], max_length=1)),
                ('matched', models.BooleanField()),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prediction_responses', to='experiment.sessionmember')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prediction_responses', to='experiment.session')),
                ('trial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='experiment.trial16')),
            ],
            options={
                'ordering': ['trial__number'],
                'unique_together': {('session', 'member', 'trial')},
            },
        ),
    ]
