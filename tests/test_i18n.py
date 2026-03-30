from app.i18n import translate, SUPPORTED_LANGS


def test_translate_returns_portuguese_string():
    assert translate("header.profile", "pt") == "Meu Perfil"


def test_translate_returns_english_string():
    assert translate("header.profile", "en") == "My Profile"


def test_translate_returns_spanish_string():
    assert translate("header.profile", "es") == "Mi Perfil"


def test_translate_falls_back_to_pt_for_missing_key():
    result = translate("header.profile", "xx")
    assert result == "Meu Perfil"


def test_translate_returns_key_when_not_found_anywhere():
    assert translate("nonexistent.key", "en") == "nonexistent.key"


def test_supported_langs():
    assert SUPPORTED_LANGS == {"en", "pt", "es"}
