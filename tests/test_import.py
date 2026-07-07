"""Smoke test: the app package imports."""


def test_app_imports() -> None:
    import app

    assert app.__version__
