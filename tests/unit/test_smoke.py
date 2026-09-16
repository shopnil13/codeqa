def test_settings_load() -> None:
    from codeqa.config import get_settings

    settings = get_settings()
    assert settings.app_name == "CodeQA"
