# Generated migration for Week 1 Quality Validation fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitals', '0005_predictiveriskassessment_forecast_30d_bp_systolic_and_more'),
    ]

    operations = [
        # Add quality validation fields to VitalSigns
        migrations.AddField(
            model_name='vitalsigns',
            name='quality_score',
            field=models.FloatField(blank=True, null=True, help_text='0-100 quality score'),
        ),
        migrations.AddField(
            model_name='vitalsigns',
            name='is_approved',
            field=models.BooleanField(default=True, help_text='Passed quality validation'),
        ),
        migrations.AddField(
            model_name='vitalsigns',
            name='quality_check_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vitalsigns',
            name='quality_check_notes',
            field=models.TextField(blank=True, help_text='Validation issues and warnings'),
        ),

        # Create PatientBaselineData model
        migrations.CreateModel(
            name='PatientBaselineData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vital_name', models.CharField(max_length=50)),
                ('mean_value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('std_dev', models.DecimalField(decimal_places=2, max_digits=8)),
                ('min_value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('max_value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('median_value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('percentile_5', models.DecimalField(decimal_places=2, max_digits=8)),
                ('percentile_25', models.DecimalField(decimal_places=2, max_digits=8)),
                ('percentile_75', models.DecimalField(decimal_places=2, max_digits=8)),
                ('percentile_95', models.DecimalField(decimal_places=2, max_digits=8)),
                ('normal_range_lower', models.DecimalField(decimal_places=2, max_digits=8)),
                ('normal_range_upper', models.DecimalField(decimal_places=2, max_digits=8)),
                ('n_samples', models.IntegerField(help_text='Number of measurements used')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('clinical_notes', models.TextField(blank=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='baseline_data', to='patients.patient')),
            ],
            options={
                'verbose_name_plural': 'Patient Baseline Data',
                'ordering': ['patient', 'vital_name'],
            },
        ),

        # Add unique constraint
        migrations.AlterUniqueTogether(
            name='patientbaselinedata',
            unique_together={('patient', 'vital_name')},
        ),
    ]
