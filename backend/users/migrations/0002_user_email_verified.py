from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_verified',
            field=models.BooleanField(
                default=True,
                help_text='New self-registered accounts must verify their email before signing in.',
            ),
        ),
    ]
