# Generated by Django 2.0.7 on 2018-09-05 06:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twos_rest_api', '0011_snap'),
    ]

    operations = [
        migrations.AddField(
            model_name='error',
            name='channel_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='snap',
            name='last_update_time',
            field=models.DateTimeField(null=True),
        ),
    ]
