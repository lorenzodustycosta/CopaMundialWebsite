# Generated by Django 5.0.3 on 2024-05-07 07:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0003_alter_player_name_alter_player_surname'),
    ]

    operations = [
        migrations.AlterField(
            model_name='player',
            name='name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='player',
            name='surname',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]