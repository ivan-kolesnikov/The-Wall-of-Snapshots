# Generated by Django 2.0.7 on 2018-09-04 13:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twos_rest_api', '0010_auto_20180904_1641'),
    ]

    operations = [
        migrations.CreateModel(
            name='Snap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_id', models.PositiveIntegerField()),
                ('snap_location', models.CharField(max_length=500)),
            ],
        ),
    ]