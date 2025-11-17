from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_add_database_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='last_login_at',
            field=models.DateTimeField(blank=True, help_text='Timestamp of the most recent successful login', null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='last_login_ip',
            field=models.GenericIPAddressField(blank=True, help_text='IP address used for the most recent login', null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='last_login_user_agent',
            field=models.CharField(blank=True, help_text='User agent string captured at last login', max_length=512),
        ),
    ]

