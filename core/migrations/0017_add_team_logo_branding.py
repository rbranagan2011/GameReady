# Generated manually for Team logo branding fields

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_add_player_personal_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='logo',
            field=models.ImageField(blank=True, help_text='Team logo for branding', null=True, upload_to='team_logos/'),
        ),
        migrations.AddField(
            model_name='team',
            name='logo_display_mode',
            field=models.CharField(
                choices=[
                    ('NONE', 'No Logo'),
                    ('HEADER', 'Header Logo Only'),
                    ('BACKGROUND', 'Background Only'),
                    ('BOTH', 'Header + Background'),
                ],
                default='NONE',
                help_text='How to display the team logo',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='team',
            name='background_opacity',
            field=models.FloatField(
                default=0.05,
                help_text='Background logo opacity (0.01-0.5)',
                validators=[
                    django.core.validators.MinValueValidator(0.01),
                    django.core.validators.MaxValueValidator(0.5)
                ]
            ),
        ),
        migrations.AddField(
            model_name='team',
            name='background_position',
            field=models.CharField(
                choices=[
                    ('CENTER', 'Center'),
                    ('TOP_LEFT', 'Top Left'),
                    ('TOP_RIGHT', 'Top Right'),
                    ('BOTTOM_LEFT', 'Bottom Left'),
                    ('BOTTOM_RIGHT', 'Bottom Right'),
                ],
                default='CENTER',
                help_text='Background logo position',
                max_length=20
            ),
        ),
    ]



