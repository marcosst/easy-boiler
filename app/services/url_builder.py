def timestamp_to_seconds(timestamp: str) -> int:
    """Convert HH:MM:SS to total seconds."""
    parts = timestamp.split(":")
    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
    return h * 3600 + m * 60 + s


def build_step_url(youtube_id: str, timestamp: str) -> str:
    """Build YouTube URL with timestamp parameter."""
    seconds = timestamp_to_seconds(timestamp)
    return f"https://www.youtube.com/watch?v={youtube_id}&t={seconds}s"
