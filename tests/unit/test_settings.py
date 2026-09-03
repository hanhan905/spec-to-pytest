from framework.config.settings import Settings


def test_settings_validate_timeout() -> None:
    settings = Settings(default_timeout_ms=2500)
    assert settings.default_timeout_ms == 2500
    assert settings.base_url.startswith("http://")
