from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='address',
            field=models.CharField(blank=True, max_length=255, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='store',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, default=''),
            preserve_default=False,
        ),
    ]
