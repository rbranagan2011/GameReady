# Generated manually for database performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_featurerequest_featurerequestcomment'),
    ]

    operations = [
        # ReadinessReport indexes
        migrations.AddIndex(
            model_name='readinessreport',
            index=models.Index(fields=['athlete', 'date_created'], name='rr_athlete_date_idx'),
        ),
        migrations.AddIndex(
            model_name='readinessreport',
            index=models.Index(fields=['date_created'], name='rr_date_idx'),
        ),
        # PlayerPersonalLabel indexes
        migrations.AddIndex(
            model_name='playerpersonallabel',
            index=models.Index(fields=['athlete', 'date'], name='ppl_athlete_date_idx'),
        ),
        # Profile indexes
        migrations.AddIndex(
            model_name='profile',
            index=models.Index(fields=['role'], name='profile_role_idx'),
        ),
        # FeatureRequest indexes
        migrations.AddIndex(
            model_name='featurerequest',
            index=models.Index(fields=['created_at'], name='featurerequest_created_idx'),
        ),
        migrations.AddIndex(
            model_name='featurerequest',
            index=models.Index(fields=['request_type'], name='featurerequest_type_idx'),
        ),
        # EmailVerification indexes
        migrations.AddIndex(
            model_name='emailverification',
            index=models.Index(fields=['expires_at'], name='emailverification_expires_idx'),
        ),
    ]

