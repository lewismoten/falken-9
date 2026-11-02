"""Cross-surface integration checks for the final consumer release."""
from scripts.build_public_pages import curated


def test_consumer_provenance_files_remain_local_in_the_website():
    for name in ('assets/interpretability/presentation-inventory.json',
                 'provenance/application-screenshot-provenance.json',
                 'provenance/application-validation.json'):
        assert curated(name), name
