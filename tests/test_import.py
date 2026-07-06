"""Smoke test: the speedlog package imports."""


def test_speedlog_imports() -> None:
    import speedlog

    assert speedlog.__version__
