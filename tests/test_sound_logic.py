import time
from config import Config


def should_play_sound(last_played_timestamp, now_ts=None, cooldown_ms=None):
    """Simple helper to decide if a sound should play for a student.
    last_played_timestamp: epoch ms or None
    now_ts: epoch ms (defaults to current time)
    cooldown_ms: cooldown in ms (defaults to Config.SOUND_COOLDOWN_MS)
    """
    if now_ts is None:
        now_ts = int(time.time() * 1000)
    if cooldown_ms is None:
        cooldown_ms = getattr(Config, 'SOUND_COOLDOWN_MS', 30000)
    if not last_played_timestamp:
        return True
    return (now_ts - last_played_timestamp) > cooldown_ms


def test_sound_allowed_when_never_played():
    assert should_play_sound(None)


def test_sound_blocked_if_recently_played():
    now = int(time.time() * 1000)
    assert not should_play_sound(now - (getattr(Config, 'SOUND_COOLDOWN_MS', 30000) - 1000), now_ts=now)


def test_sound_allowed_after_cooldown():
    now = int(time.time() * 1000)
    assert should_play_sound(now - (getattr(Config, 'SOUND_COOLDOWN_MS', 30000) + 1000), now_ts=now)
