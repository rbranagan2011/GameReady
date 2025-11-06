# Generated manually for PlayerPersonalLabel model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0015_add_multiple_teams_and_reminder_toggle'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlayerPersonalLabel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('label', models.CharField(help_text="Player's personal label for this day (e.g., 'Gym session', 'Personal training')", max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('athlete', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='personal_labels', to='auth.user')),
            ],
            options={
                'ordering': ['date'],
                'unique_together': {('athlete', 'date')},
            },
        ),
    ]

