from __future__ import annotations

import asyncio
import time

import numpy as np
import pytest

from opentalking.core.types.frames import VideoFrameData
from opentalking.pipeline.speak.synthesis_runner import FlashTalkRunner


class _FakeQueue:
    def __init__(self, maxsize: int = 0) -> None:
        self.items: list[object] = []
        self.maxsize = maxsize

    async def put(self, item: object) -> None:
        self.items.append(item)

    def put_nowait(self, item: object) -> None:
        if self.full():
            raise asyncio.QueueFull
        self.items.append(item)

    def get_nowait(self) -> object:
        return self.items.pop(0)

    def qsize(self) -> int:
        return len(self.items)

    def full(self) -> bool:
        return self.maxsize > 0 and len(self.items) >= self.maxsize


class _FakeTrack:
    def __init__(self) -> None:
        self._queue = _FakeQueue()


class _FakeWebRTC:
    def __init__(self) -> None:
        self.video = _FakeTrack()
        self.audio = _FakeTrack()
        self.draining = False


class _FakeAudio2Video:
    sample_rate = 16000
    fps = 25


class _FakeRedis:
    async def hget(self, *_args: object, **_kwargs: object) -> str:
        return "0"


def _runner() -> FlashTalkRunner:
    runner = object.__new__(FlashTalkRunner)
    runner.session_id = "sess_av_sync"
    runner.model_type = "quicktalk"
    runner.redis = _FakeRedis()
    runner.flashtalk = _FakeAudio2Video()
    runner.webrtc = _FakeWebRTC()
    runner._media_ws_clients = set()
    runner._media_ws_jpeg_quality = 70
    runner._speech_media_active = True
    runner._webrtc_started = asyncio.Event()
    runner._webrtc_started.set()
    runner._webrtc_connected = True
    runner._interrupt = asyncio.Event()
    runner._closed = False
    runner._av_ts_ms = 0.0
    runner._last_frame = None
    runner._recording_frame_index = 0
    runner._debug_frame_trace = False
    runner._debug_prev_video_mean = None
    runner._debug_queued_video_count = 0
    runner._speak_t0_wall = None
    runner._speak_milestones = None
    runner._speak_enqueue_unix = None
    runner._media_playback_wall_start = None
    runner._speech_media_drain_until_wall = None
    return runner


def _frame(value: int) -> VideoFrameData:
    data = np.full((2, 2, 3), value, dtype=np.uint8)
    return VideoFrameData(data=data, width=2, height=2, timestamp_ms=-1.0)


@pytest.mark.asyncio
async def test_queue_av_chunk_interleaves_timestamped_media_ws_events() -> None:
    runner = _runner()
    media_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
    runner._media_ws_clients.add(media_queue)

    await runner._queue_av_chunk(
        np.arange(1280, dtype=np.int16),
        [_frame(1), _frame(2)],
    )

    events: list[dict[str, object]] = []
    while not media_queue.empty():
        event = media_queue.get_nowait()
        assert event is not None
        events.append(event)

    assert [event["type"] for event in events] == ["video", "audio", "video", "audio"]
    assert [event["timestamp_ms"] for event in events] == [0.0, 0.0, 40.0, 40.0]
    assert [event["speech"] for event in events] == [True, True, True, True]
    assert events[1]["duration_ms"] == 40.0
    assert events[3]["duration_ms"] == 40.0
    assert runner._av_ts_ms == 80.0


@pytest.mark.asyncio
async def test_queue_av_chunk_timestamped_audio_when_no_frames() -> None:
    runner = _runner()
    media_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
    runner._media_ws_clients.add(media_queue)

    await runner._queue_av_chunk(np.arange(2560, dtype=np.int16), [])

    event = media_queue.get_nowait()
    assert event is not None
    assert event["type"] == "audio"
    assert event["speech"] is True
    assert event["timestamp_ms"] == 0.0
    assert event["duration_ms"] == 160.0
    assert event["samples"] == 2560
    assert media_queue.empty()
    assert runner._av_ts_ms == 160.0


def test_quicktalk_audio_delay_prepends_silence_once() -> None:
    runner = _runner()
    runner._quicktalk_audio_delay_ms = 100.0

    first = runner._maybe_delay_quicktalk_audio(
        np.array([1, 2, 3], dtype=np.int16),
        16000,
        already_delayed=False,
    )
    second = runner._maybe_delay_quicktalk_audio(
        np.array([4, 5], dtype=np.int16),
        16000,
        already_delayed=True,
    )

    assert first.shape[0] == 1603
    assert np.all(first[:1600] == 0)
    assert first[-3:].tolist() == [1, 2, 3]
    assert second.tolist() == [4, 5]


@pytest.mark.asyncio
async def test_media_ws_playback_does_not_fill_disconnected_webrtc_queues() -> None:
    runner = _runner()
    runner._webrtc_connected = False
    media_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
    runner._media_ws_clients.add(media_queue)

    await runner._queue_av_chunk(
        np.arange(1280, dtype=np.int16),
        [_frame(1), _frame(2)],
    )

    assert runner.webrtc.video._queue.qsize() == 0
    assert runner.webrtc.audio._queue.qsize() == 0
    assert media_queue.qsize() == 4


@pytest.mark.asyncio
async def test_media_ws_playback_backpressure_waits_when_timeline_is_far_ahead(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIO2VIDEO_PLAYBACK_MAX_WAIT_MS", "40")
    runner = _runner()
    runner._webrtc_connected = False
    runner._media_ws_clients.add(asyncio.Queue())
    runner._media_playback_wall_start = time.perf_counter() - 0.01
    runner._av_ts_ms = 5000.0

    waited_ms = await runner._wait_for_playback_capacity(
        n_frames=4,
        first_media_this_speak=False,
    )

    assert waited_ms > 0


def test_speech_media_drain_pending_until_generated_timeline_catches_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENTALKING_SPEECH_IDLE_DRAIN_CUSHION_MS", "20")
    runner = _runner()
    runner._av_ts_ms = 1000.0
    runner._media_playback_wall_start = time.perf_counter()

    runner._mark_speech_media_drain()

    assert runner._speech_media_drain_pending() is True
    runner._speech_media_drain_until_wall = time.perf_counter() - 0.01
    assert runner._speech_media_drain_pending() is False


@pytest.mark.asyncio
async def test_idle_tick_skips_while_speech_media_is_draining(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENTALKING_SPEECH_IDLE_DRAIN_CUSHION_MS", "20")
    runner = _runner()
    runner._speech_media_active = False
    runner._idle_frames = [_frame(8).data]
    runner._idle_playback_indices = []
    runner._idle_frame_idx = 0
    runner._media_playback_wall_start = time.perf_counter()
    runner._av_ts_ms = 1000.0
    runner._mark_speech_media_drain()

    await runner._idle_tick()

    assert runner.webrtc.video._queue.qsize() == 0
