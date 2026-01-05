from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("tournament", "0014_group_note"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE tournament_match DROP COLUMN IF EXISTS pitch;",
            reverse_sql="""
                ALTER TABLE tournament_match
                ADD COLUMN pitch varchar(50) NOT NULL DEFAULT 'Da definire';
            """,
        ),
    ]