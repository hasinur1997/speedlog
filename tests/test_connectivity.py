"""Tests for app.collector.connectivity (NST-304).

A fake if-stats source drives the watcher; recording fakes for repository,
segmenter and smoother capture every call into one shared event list so
ordering across collaborators can be asserted exactly.
"""

from __future__ import annotations

from collections.abc import Mapping

from app import config
from app.collector.connectivity import ConnectivityWatcher

DEBOUNCE = 3

Event = tuple


class FakeIfStats:
    """Scripted interface stats: tests mutate ``stats`` between ticks."""

    def __init__(self, stats: dict[str, bool]) -> None:
        self.stats = stats

    def read_if_stats(self) -> Mapping[str, bool]:
        return dict(self.stats)

    def set_online(self, online: bool) -> None:
        self.stats = {"en0": online}


class FakeRepository:
    def __init__(self, events: list[Event]) -> None:
        self._events = events
        self._next_id = 1

    def close_dangling_sessions(self, ts: int) -> int:
        self._events.append(("close_dangling", ts))
        return 0

    def start_session(self, ts: int) -> int:
        session_id = self._next_id
        self._next_id += 1
        self._events.append(("start_session", session_id, ts))
        return session_id

    def end_session(self, session_id: int, ts: int, reason: str) -> None:
        self._events.append(("end_session", session_id, ts, reason))


class FakeSegmenter:
    def __init__(self, events: list[Event]) -> None:
        self._events = events

    def flush(self, now: int, session_id: int) -> None:
        self._events.append(("flush", now, session_id))


class FakeSmoother:
    def __init__(self, events: list[Event]) -> None:
        self._events = events

    def reset(self) -> None:
        self._events.append(("reset",))


def make_watcher(
    events: list[Event], source: FakeIfStats, debounce_ticks: int = DEBOUNCE
) -> ConnectivityWatcher:
    return ConnectivityWatcher(
        source=source,
        repository=FakeRepository(events),
        segmenter=FakeSegmenter(events),
        smoother=FakeSmoother(events),
        debounce_ticks=debounce_ticks,
        on_session_started=lambda session_id, ts: events.append(("started", session_id, ts)),
        on_session_ended=lambda session_id, ts: events.append(("ended", session_id, ts)),
    )


# --- check(): raw interface logic ---------------------------------------


def test_check_online_when_real_interface_up() -> None:
    watcher = make_watcher([], FakeIfStats({"lo0": True, "en0": True}))
    assert watcher.check() is True


def test_check_offline_when_only_excluded_interfaces_up() -> None:
    watcher = make_watcher([], FakeIfStats({"lo0": True, "awdl0": True, "utun3": True}))
    assert watcher.check() is False


def test_check_offline_when_real_interface_down() -> None:
    watcher = make_watcher([], FakeIfStats({"en0": False, "lo0": True}))
    assert watcher.check() is False


def test_check_offline_with_no_interfaces() -> None:
    watcher = make_watcher([], FakeIfStats({}))
    assert watcher.check() is False


# --- start(): dangling recovery + initial state --------------------------


def test_start_while_online_opens_session_immediately() -> None:
    events: list[Event] = []
    watcher = make_watcher(events, FakeIfStats({"en0": True}))

    watcher.start(now=100)

    assert events == [("close_dangling", 100), ("start_session", 1, 100), ("started", 1, 100)]
    assert watcher.online is True
    assert watcher.session_id == 1


def test_start_while_offline_opens_no_session() -> None:
    events: list[Event] = []
    watcher = make_watcher(events, FakeIfStats({"en0": False}))

    watcher.start(now=100)

    assert events == [("close_dangling", 100)]
    assert watcher.online is False
    assert watcher.session_id is None


def test_dangling_recovery_invoked_once_at_start() -> None:
    events: list[Event] = []
    source = FakeIfStats({"en0": True})
    watcher = make_watcher(events, source)

    watcher.start(now=100)
    for now in range(101, 120):
        watcher.tick(now)

    assert [event for event in events if event[0] == "close_dangling"] == [("close_dangling", 100)]


# --- tick(): debounce ----------------------------------------------------


def test_offline_flap_shorter_than_debounce_is_ignored() -> None:
    events: list[Event] = []
    source = FakeIfStats({"en0": True})
    watcher = make_watcher(events, source)
    watcher.start(now=100)

    source.set_online(False)
    watcher.tick(101)
    watcher.tick(102)  # only 2 offline checks: below the threshold
    source.set_online(True)
    watcher.tick(103)  # back online: pending run discarded
    source.set_online(False)
    watcher.tick(104)
    watcher.tick(105)

    assert watcher.online is True
    assert watcher.session_id == 1
    assert [event for event in events if event[0] == "end_session"] == []


def test_disconnect_confirmed_after_debounce_ticks() -> None:
    events: list[Event] = []
    source = FakeIfStats({"en0": True})
    watcher = make_watcher(events, source)
    watcher.start(now=100)
    del events[:]

    source.set_online(False)
    watcher.tick(101)
    watcher.tick(102)
    watcher.tick(103)  # third consecutive offline check confirms

    assert events == [
        ("flush", 103, 1),
        ("end_session", 1, 103, "disconnect"),
        ("ended", 1, 103),
        ("reset",),
    ]
    assert watcher.online is False
    assert watcher.session_id is None


def test_reconnect_confirmed_after_debounce_ticks_opens_new_session() -> None:
    events: list[Event] = []
    source = FakeIfStats({"en0": False})
    watcher = make_watcher(events, source)
    watcher.start(now=100)
    del events[:]

    source.set_online(True)
    watcher.tick(101)
    watcher.tick(102)
    assert watcher.session_id is None  # not yet confirmed
    watcher.tick(103)

    assert events == [("start_session", 1, 103), ("started", 1, 103)]
    assert watcher.online is True
    assert watcher.session_id == 1


def test_full_disconnect_reconnect_cycle_uses_new_session_id() -> None:
    events: list[Event] = []
    source = FakeIfStats({"en0": True})
    watcher = make_watcher(events, source)
    watcher.start(now=100)

    source.set_online(False)
    for now in range(101, 101 + DEBOUNCE):
        watcher.tick(now)
    source.set_online(True)
    for now in range(110, 110 + DEBOUNCE):
        watcher.tick(now)

    assert watcher.session_id == 2
    assert [event for event in events if event[0] == "start_session"] == [
        ("start_session", 1, 100),
        ("start_session", 2, 112),
    ]


def test_in_state_check_resets_pending_counter() -> None:
    events: list[Event] = []
    source = FakeIfStats({"en0": True})
    watcher = make_watcher(events, source)
    watcher.start(now=100)

    # 2 offline, 1 online, 2 offline: never 3 consecutive -> no transition.
    source.set_online(False)
    watcher.tick(101)
    watcher.tick(102)
    source.set_online(True)
    watcher.tick(103)
    source.set_online(False)
    watcher.tick(104)
    watcher.tick(105)

    assert watcher.online is True


def test_default_debounce_comes_from_config() -> None:
    watcher = ConnectivityWatcher(
        source=FakeIfStats({}),
        repository=FakeRepository([]),
        segmenter=FakeSegmenter([]),
        smoother=FakeSmoother([]),
    )
    assert watcher._debounce_ticks == config.CONNECTIVITY_DEBOUNCE_TICKS
