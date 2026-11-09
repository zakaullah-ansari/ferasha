"""pg_trgm, for catalogue search's tolerance of spelling slips (catalog/search.py)."""

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_product_face_coverage_and_more")]

    operations = [TrigramExtension()]
