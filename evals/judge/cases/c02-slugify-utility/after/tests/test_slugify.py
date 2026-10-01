from utils.slugify import slugify


def test_slugify_handles_accents_and_punctuation():
    assert slugify("Café: Déjà vu!") == "cafe-deja-vu"
