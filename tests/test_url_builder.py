from app.services.url_builder import timestamp_to_seconds, build_step_url


def test_timestamp_to_seconds_basic():
    assert timestamp_to_seconds("00:01:03") == 63


def test_timestamp_to_seconds_zero():
    assert timestamp_to_seconds("00:00:00") == 0


def test_timestamp_to_seconds_hours():
    assert timestamp_to_seconds("01:30:00") == 5400


def test_timestamp_to_seconds_all_parts():
    assert timestamp_to_seconds("02:15:45") == 8145


def test_build_step_url():
    url = build_step_url("abc123", "00:01:03")
    assert url == "https://www.youtube.com/watch?v=abc123&t=63s"


def test_build_step_url_zero():
    url = build_step_url("xyz789", "00:00:00")
    assert url == "https://www.youtube.com/watch?v=xyz789&t=0s"
