import { apiPost, buildWsUrl } from "./api";

function requestVideoPlayback(videoEl: HTMLVideoElement) {
  videoEl.autoplay = true;
  videoEl.playsInline = true;
  const attempt = () => {
    void videoEl.play().catch(() => {
      // If the browser blocks autoplay with audio, retry muted so video still paints.
      videoEl.muted = true;
      void videoEl.play().catch(() => {});
    });
  };
  attempt();
  return attempt;
}

export type PlaybackHandle = {
  pc: RTCPeerConnection;
  remoteStream: MediaStream;
  close?: () => void;
};

export type StartPlaybackOptions = {
  onRemoteStream?: (remoteStream: MediaStream) => void;
};

type MediaWsVideoEvent = {
  type: "video";
  format: "jpeg";
  speech?: boolean;
  width: number;
  height: number;
  timestamp_ms?: number;
  data: string;
};

type MediaWsAudioEvent = {
  type: "audio";
  format: "pcm_s16le";
  speech?: boolean;
  sample_rate: number;
  samples: number;
  timestamp_ms?: number;
  duration_ms?: number;
  data: string;
};

type MediaWsEvent =
  | { type: "ready"; fps?: number; sample_rate?: number }
  | { type: "initializing"; session_id?: string }
  | { type: "error"; message?: string }
  | MediaWsVideoEvent
  | MediaWsAudioEvent;

type MediaFallbackHandle = {
  stream: MediaStream;
  close: () => void;
};

function bytesFromBase64(data: string): Uint8Array {
  const binary = atob(data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function createAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  const AudioContextCtor =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextCtor) return null;
  try {
    const ctx = new AudioContextCtor();
    void ctx.resume().catch(() => {});
    return ctx;
  } catch {
    return null;
  }
}

function schedulePcmAudio(
  ctx: AudioContext,
  event: MediaWsAudioEvent,
  nextAudioTimeRef: { current: number },
  destination?: MediaStreamAudioDestinationNode | null,
): number | null {
  const bytes = bytesFromBase64(event.data);
  const pcm = new Int16Array(bytes.buffer, bytes.byteOffset, Math.floor(bytes.byteLength / 2));
  if (!pcm.length) return null;
  const sampleRate = Math.max(1, Number(event.sample_rate) || 16000);
  const buffer = ctx.createBuffer(1, pcm.length, sampleRate);
  const channel = buffer.getChannelData(0);
  for (let i = 0; i < pcm.length; i += 1) {
    channel[i] = Math.max(-1, Math.min(1, pcm[i] / 32768));
  }
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.connect(ctx.destination);
  if (destination) source.connect(destination);
  const startAt = Math.max(ctx.currentTime + 0.02, nextAudioTimeRef.current || 0);
  source.start(startAt);
  nextAudioTimeRef.current = startAt + buffer.duration;
  return startAt;
}

function numberFromEnv(value: string | undefined, fallback: number): number {
  if (value == null || value.trim() === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const MEDIA_WS_VIDEO_DELAY_MS = Math.max(
  0,
  numberFromEnv(import.meta.env.VITE_MEDIA_WS_VIDEO_DELAY_MS, 80),
);

function startMediaWebSocketFallback(
  sessionId: string,
  videoEl: HTMLVideoElement,
  options: StartPlaybackOptions,
  audioCtx: AudioContext | null,
): MediaFallbackHandle {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const stream = canvas.captureStream(25);
  const audioDestination = audioCtx?.createMediaStreamDestination() ?? null;
  if (audioDestination) {
    for (const track of audioDestination.stream.getAudioTracks()) {
      stream.addTrack(track);
    }
  }
  const ws = new WebSocket(buildWsUrl(`/sessions/${sessionId}/media`));
  const ensurePlayback = requestVideoPlayback(videoEl);
  const nextAudioTimeRef = { current: audioCtx?.currentTime ?? 0 };
  const videoTimers = new Set<number>();
  const pendingSpeechVideos: MediaWsVideoEvent[] = [];
  let lastSpeechVideoTargetTime: number | null = null;
  let pendingIdleVideoEvent: MediaWsVideoEvent | null = null;
  let pendingIdleVideoTimer: number | null = null;
  const mediaClockRef = {
    audioStartTime: null as number | null,
    audioStartTimestampMs: null as number | null,
    lastAudioTimestampMs: null as number | null,
    lastVideoTimestampMs: null as number | null,
  };
  let closed = false;

  // Audio is rendered through AudioContext below. Keep the video element muted so
  // the MediaStreamAudioDestinationNode track is available for recording without
  // also being played by the element.
  videoEl.muted = true;
  videoEl.srcObject = stream;
  options.onRemoteStream?.(stream);
  ensurePlayback();

  const clearVideoTimers = () => {
    for (const timer of videoTimers) window.clearTimeout(timer);
    videoTimers.clear();
  };

  const clearPendingIdleVideo = () => {
    if (pendingIdleVideoTimer !== null) {
      window.clearTimeout(pendingIdleVideoTimer);
      pendingIdleVideoTimer = null;
    }
    pendingIdleVideoEvent = null;
  };

  const resetSpeechTimeline = () => {
    clearVideoTimers();
    clearPendingIdleVideo();
    pendingSpeechVideos.length = 0;
    lastSpeechVideoTargetTime = null;
    mediaClockRef.audioStartTime = null;
    mediaClockRef.audioStartTimestampMs = null;
    mediaClockRef.lastAudioTimestampMs = null;
    mediaClockRef.lastVideoTimestampMs = null;
    if (audioCtx) nextAudioTimeRef.current = audioCtx.currentTime;
  };

  const drawVideoEvent = (event: MediaWsVideoEvent) => {
    if (closed || !ctx) return;
    const bytes = bytesFromBase64(event.data);
    const blob = new Blob([bytes], { type: "image/jpeg" });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      if (closed) {
        URL.revokeObjectURL(url);
        return;
      }
      if (event.width > 0 && event.height > 0) {
        if (canvas.width !== event.width) canvas.width = event.width;
        if (canvas.height !== event.height) canvas.height = event.height;
      } else if (!canvas.width || !canvas.height) {
        canvas.width = img.naturalWidth || 640;
        canvas.height = img.naturalHeight || 360;
      }
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      ensurePlayback();
    };
    img.onerror = () => URL.revokeObjectURL(url);
    img.src = url;
  };

  const hasPendingSpeechPlayback = () => {
    if (!audioCtx) return false;
    if (pendingSpeechVideos.length > 0 || videoTimers.size > 0) return true;
    return lastSpeechVideoTargetTime !== null
      && audioCtx.currentTime < lastSpeechVideoTargetTime + 0.08;
  };

  const deferIdleVideoEvent = (event: MediaWsVideoEvent) => {
    if (!audioCtx) {
      drawVideoEvent(event);
      return;
    }
    pendingIdleVideoEvent = event;
    if (pendingIdleVideoTimer !== null) window.clearTimeout(pendingIdleVideoTimer);
    const target = Math.max(audioCtx.currentTime, lastSpeechVideoTargetTime ?? audioCtx.currentTime) + 0.08;
    const delayMs = Math.max(20, (target - audioCtx.currentTime) * 1000);
    pendingIdleVideoTimer = window.setTimeout(() => {
      pendingIdleVideoTimer = null;
      const latest = pendingIdleVideoEvent;
      pendingIdleVideoEvent = null;
      if (!latest) return;
      if (hasPendingSpeechPlayback()) {
        deferIdleVideoEvent(latest);
        return;
      }
      drawVideoEvent(latest);
    }, delayMs);
  };

  const scheduleVideoEvent = (event: MediaWsVideoEvent) => {
    if (!event.speech) {
      if (hasPendingSpeechPlayback()) {
        deferIdleVideoEvent(event);
        return;
      }
      drawVideoEvent(event);
      return;
    }
    const timestampMs = Number(event.timestamp_ms ?? 0);
    const lastVideoTs = mediaClockRef.lastVideoTimestampMs;
    if (lastVideoTs !== null && timestampMs + 1 < lastVideoTs) {
      resetSpeechTimeline();
    }
    mediaClockRef.lastVideoTimestampMs = timestampMs;
    if (!audioCtx) {
      drawVideoEvent(event);
      return;
    }
    if (mediaClockRef.audioStartTime === null || mediaClockRef.audioStartTimestampMs === null) {
      pendingSpeechVideos.push(event);
      if (pendingSpeechVideos.length > 300) pendingSpeechVideos.shift();
      return;
    }
    const target =
      mediaClockRef.audioStartTime
      + (timestampMs - mediaClockRef.audioStartTimestampMs + MEDIA_WS_VIDEO_DELAY_MS) / 1000;
    lastSpeechVideoTargetTime = Math.max(lastSpeechVideoTargetTime ?? target, target);
    const delayMs = Math.max(0, (target - audioCtx.currentTime) * 1000);
    const timer = window.setTimeout(() => {
      videoTimers.delete(timer);
      drawVideoEvent(event);
    }, delayMs);
    videoTimers.add(timer);
  };

  const flushPendingSpeechVideos = () => {
    if (!pendingSpeechVideos.length) return;
    const pending = pendingSpeechVideos.splice(0, pendingSpeechVideos.length);
    for (const videoEvent of pending) scheduleVideoEvent(videoEvent);
  };

  ws.onmessage = (message) => {
    if (closed || typeof message.data !== "string") return;
    let event: MediaWsEvent;
    try {
      event = JSON.parse(message.data) as MediaWsEvent;
    } catch {
      return;
    }
    if (event.type === "video" && event.format === "jpeg" && ctx) {
      scheduleVideoEvent(event);
      return;
    }
    if (event.type === "audio" && event.format === "pcm_s16le" && audioCtx) {
      void audioCtx.resume().catch(() => {});
      const timestampMs = Number(event.timestamp_ms ?? 0);
      const lastAudioTs = mediaClockRef.lastAudioTimestampMs;
      if (event.speech && lastAudioTs !== null && timestampMs + 1 < lastAudioTs) {
        resetSpeechTimeline();
      }
      const startAt = schedulePcmAudio(audioCtx, event, nextAudioTimeRef, audioDestination);
      if (event.speech && startAt !== null && mediaClockRef.audioStartTime === null) {
        mediaClockRef.audioStartTime = startAt;
        mediaClockRef.audioStartTimestampMs = timestampMs;
        flushPendingSpeechVideos();
      }
      if (event.speech) mediaClockRef.lastAudioTimestampMs = timestampMs;
    }
  };

  return {
    stream,
    close: () => {
      closed = true;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      clearVideoTimers();
      clearPendingIdleVideo();
      for (const track of stream.getTracks()) track.stop();
    },
  };
}

export async function startPlayback(
  sessionId: string,
  videoEl: HTMLVideoElement,
  options: StartPlaybackOptions = {},
): Promise<PlaybackHandle> {
  const pc = new RTCPeerConnection({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
  });
  const mediaStream = new MediaStream();
  let fallback: MediaFallbackHandle | null = null;
  let fallbackAudioCtx: AudioContext | null = null;
  let fallbackTimer: number | null = null;
  let closed = false;
  let webRtcVideoReady = false;

  videoEl.srcObject = mediaStream;
  const ensurePlayback = requestVideoPlayback(videoEl);

  const startFallback = () => {
    if (closed || fallback) return;
    fallbackAudioCtx = createAudioContext();
    fallback = startMediaWebSocketFallback(
      sessionId,
      videoEl,
      options,
      fallbackAudioCtx,
    );
  };

  const cancelFallbackTimer = () => {
    if (fallbackTimer === null) return;
    window.clearTimeout(fallbackTimer);
    fallbackTimer = null;
  };

  const hasWebRtcVideoFrame = () =>
    videoEl.srcObject === mediaStream && videoEl.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA;

  const switchToWebRtcIfReady = () => {
    if (closed || !hasWebRtcVideoFrame()) return;
    webRtcVideoReady = true;
    cancelFallbackTimer();
    if (!fallback) return;
    fallback.close();
    fallback = null;
    void fallbackAudioCtx?.close().catch(() => {});
    fallbackAudioCtx = null;
    videoEl.srcObject = mediaStream;
    ensurePlayback();
  };

  videoEl.addEventListener("loadeddata", switchToWebRtcIfReady);
  videoEl.addEventListener("playing", switchToWebRtcIfReady);

  pc.ontrack = (ev) => {
    const track = ev.track;
    if (!track) return;
    const hasTrack = mediaStream.getTracks().some((t) => t.id === track.id);
    if (!hasTrack) {
      mediaStream.addTrack(track);
      options.onRemoteStream?.(mediaStream);
    }
    ensurePlayback();
    window.setTimeout(switchToWebRtcIfReady, 0);
  };

  const cleanup = () => {
    cancelFallbackTimer();
    videoEl.removeEventListener("loadeddata", switchToWebRtcIfReady);
    videoEl.removeEventListener("playing", switchToWebRtcIfReady);
    fallback?.close();
    fallback = null;
    void fallbackAudioCtx?.close().catch(() => {});
    fallbackAudioCtx = null;
    videoEl.pause();
    videoEl.srcObject = null;
  };
  pc.addEventListener("connectionstatechange", () => {
    if (
      pc.connectionState === "closed"
      || pc.connectionState === "failed"
      || pc.connectionState === "disconnected"
    ) {
      if (!closed && !webRtcVideoReady) {
        startFallback();
      }
    }
  });
  pc.addEventListener("iceconnectionstatechange", () => {
    if (
      pc.iceConnectionState === "closed"
      || pc.iceConnectionState === "failed"
      || pc.iceConnectionState === "disconnected"
    ) {
      if (!closed && !webRtcVideoReady) {
        startFallback();
      }
    }
  });

  pc.addTransceiver("video", { direction: "recvonly" });
  pc.addTransceiver("audio", { direction: "recvonly" });

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const answer = await apiPost<{ sdp: string; type: RTCSdpType }>(
    `/sessions/${sessionId}/webrtc/offer`,
    { sdp: pc.localDescription?.sdp ?? "", type: pc.localDescription?.type ?? "offer" },
  );

  await pc.setRemoteDescription(new RTCSessionDescription(answer));
  ensurePlayback();
  options.onRemoteStream?.(mediaStream);

  fallbackTimer = window.setTimeout(() => {
    switchToWebRtcIfReady();
    if (!webRtcVideoReady) startFallback();
  }, 2500);

  const originalClose = pc.close.bind(pc);
  pc.close = () => {
    closed = true;
    cleanup();
    originalClose();
  };

  return {
    pc,
    remoteStream: mediaStream,
    close: () => pc.close(),
  };
}
