# Generated migration for Week 3 PatientForecast model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitals', '0006_week1_quality_validation'),
    ]

    operations = [
        migrations.CreateModel(
            name='PatientForecast',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vital_name', models.CharField(max_length=50)),
                ('horizon_hours', models.IntegerField()),
                ('forecast_value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('confidence_score', models.FloatField()),
                ('prediction_interval_95_lower', models.DecimalField(decimal_places=2, max_digits=8)),
                ('prediction_interval_95_upper', models.DecimalField(decimal_places=2, max_digits=8)),
                ('prediction_interval_90_lower', models.DecimalField(decimal_places=2, max_digits=8)),
                ('prediction_interval_90_upper', models.DecimalField(decimal_places=2, max_digits=8)),
                ('forecast_reliability', models.CharField(
                    choices=[('HIGH', 'High'), ('MEDIUM', 'Medium'), ('LOW', 'Low')],
                    default='LOW',
                    max_length=10
                )),
                ('recommendation', models.TextField(blank=True)),
                ('clinical_notes', models.TextField(blank=True)),
                ('forecast_details', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('forecast_timestamp', models.DateTimeField(auto_now_add=True)),
                ('actual_value', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='Actual value when measurement taken',
                    max_digits=8,
                    null=True
                )),
                ('actual_recorded_at', models.DateTimeField(blank=True, null=True)),
                ('forecast_error', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='Absolute error from forecast',
                    max_digits=8,
                    null=True
                )),
                ('patient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='forecasts',
                    to='patients.patient'
                )),
            ],
            options={
                'verbose_name_plural': 'Patient Forecasts',
                'ordering': ['-forecast_timestamp'],
            },
        ),

        migrations.AddIndex(
            model_name='patientforecast',
            index=models.Index(fields=['patient', '-forecast_timestamp'], name='vitals_patientforecast_patient_created_idx'),
        ),
        migrations.AddIndex(
            model_name='patientforecast',
            index=models.Index(fields=['vital_name', '-forecast_timestamp'], name='vitals_patientforecast_vital_created_idx'),
        ),
    ]
