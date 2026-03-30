def test_home_contains_tailwind_dark_mode_config(auth_client):
    response = auth_client.get("/")
    assert "darkMode" in response.text


def test_home_contains_theme_manager(auth_client):
    response = auth_client.get("/")
    assert "x-data" in response.text
    assert "setTheme" in response.text


def test_home_has_dark_body_class(auth_client):
    response = auth_client.get("/")
    assert "dark:bg-neutral-900" in response.text


def test_dropdown_contains_tema_toggle(auth_client):
    response = auth_client.get("/")
    assert "Tema" in response.text


def test_dropdown_contains_theme_options(auth_client):
    response = auth_client.get("/")
    assert "setTheme('light')" in response.text
    assert "setTheme('dark')" in response.text
    assert "setTheme('auto')" in response.text


def test_home_cards_have_dark_classes(auth_client):
    response = auth_client.get("/")
    assert "dark:bg-neutral-800" in response.text
    assert "dark:border-neutral-700" in response.text


def test_home_section_title_has_dark_class(auth_client):
    response = auth_client.get("/")
    assert "dark:text-neutral-100" in response.text


def test_topics_cards_have_dark_classes(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert "dark:bg-neutral-800" in response.text
    assert "dark:border-neutral-700" in response.text


def test_topics_section_title_has_dark_class(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert "dark:text-neutral-100" in response.text
