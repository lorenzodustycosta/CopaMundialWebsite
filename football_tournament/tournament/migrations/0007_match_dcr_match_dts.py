# Generated by Django 5.0.3 on 2024-05-13 15:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0006_player_is_fake_alter_goal_match_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='dcr',
            field=models.BooleanField(default=False, verbose_name='Penalties'),
        ),
        migrations.AddField(
            model_name='match',
            name='dts',
            field=models.BooleanField(default=False, verbose_name='Overtime'),
        ),
    ]