import { apiPost } from "./api";

function requestVideoPlayback(videoEl: HTMLVideoElement) {
  videoEl.autoplay = true;
  videoEl.playsInline = true;
  videoEl.muted = true;
  const attempt = () => {
    void videoEl.play().catch(() => {
      videoEl.muted = true;
      void videoEl.play().catch(() => {});
    });
  };
  attempt();
  return attempt;
}

function requestAudioPlayback(
  audioEl: HTMLAudioElement,
  onBlocked?: (error: unknown) => void,
  muted = false,
) {
  audioEl.autoplay = true;
  audioEl.muted = muted;
  audioEl.volume = muted ? 0 : 1;
  const attempt = () => {
    const stream = audioEl.srcObject;
    if (stream instanceof MediaStream && !stream.getAudioTracks().length) return;
    void audioEl.play().catch((error) => {
      console.warn("WebRTC audio playback was blocked", error);
      onBlocked?.(error);
    });
  };
  return attempt;
}

export type PlaybackHandle = { pc: RTCPeerConnection; remoteStream: MediaStream };

export type StartPlaybackOptions = {
  audioEl?: HTMLAudioElement | null;
  audioContext?: AudioContext | null;
  onRemoteStream?: (remoteStream: MediaStream) => void;
  onRemoteTrack?: (track: MediaStreamTrack) => void;
};

export async function startPlayback(
  sessionId: string,
  videoEl: HTMLVideoElement,
  options: StartPlaybackOptions = {},
): Promise<PlaybackHandle> {
  const pc = new RTCPeerConnection({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
  });
  const remoteStream = new MediaStream();
  const videoStream = new MediaStream();
  const audioStream = new MediaStream();
  const audioEl = options.audioEl ?? null;
  const audioContext = options.audioContext ?? null;
  const useWebAudioOutput = Boolean(audioContext);
  let audioSourceNode: MediaStreamAudioSourceNode | null = null;
  let audioGainNode: GainNode | null = null;
  let webAudioFallbackEnabled = useWebAudioOutput || !audioEl;

  const enableWebAudioFallback = () => {
    webAudioFallbackEnabled = true;
    if (audioGainNode) audioGainNode.gain.value = 1;
    void audioContext?.resume().catch((error) => {
      console.warn("WebRTC AudioContext resume failed", error);
    });
  };

  const connectWebAudioOutput = () => {
    if (!audioContext || audioSourceNode || !audioStream.getAudioTracks().length) return;
    try {
      audioSourceNode = audioContext.createMediaStreamSource(audioStream);
      audioGainNode = audioContext.createGain();
      audioGainNode.gain.value = webAudioFallbackEnabled ? 1 : 0;
      audioSourceNode.connect(audioGainNode);
      audioGainNode.connect(audioContext.destination);
      void audioContext.resume().catch((error) => {
        console.warn("WebRTC AudioContext resume failed", error);
        enableWebAudioFallback();
      });
    } catch (error) {
      console.warn("WebRTC WebAudio output setup failed", error);
    }
  };

  videoEl.srcObject = videoStream;
  if (audioEl) audioEl.srcObject = audioStream;
  const ensureVideoPlayback = requestVideoPlayback(videoEl);
  const ensureAudioPlayback = audioEl
    ? requestAudioPlayback(audioEl, enableWebAudioFallback, useWebAudioOutput)
    : enableWebAudioFallback;

  pc.ontrack = (ev) => {
    const track = ev.track;
    if (!track) return;
    const hasTrack = remoteStream.getTracks().some((t) => t.id === track.id);
    if (!hasTrack) {
      remoteStream.addTrack(track);
      if (track.kind === "video") {
        videoStream.addTrack(track);
        ensureVideoPlayback();
      } else if (track.kind === "audio" && audioEl) {
        audioStream.addTrack(track);
        connectWebAudioOutput();
        ensureAudioPlayback?.();
      } else if (track.kind === "audio") {
        audioStream.addTrack(track);
        connectWebAudioOutput();
      }
      options.onRemoteTrack?.(track);
      options.onRemoteStream?.(remoteStream);
    }
  };

  const cleanup = () => {
    videoEl.pause();
    videoEl.srcObject = null;
    if (audioEl) {
      audioEl.pause();
      audioEl.srcObject = null;
    }
    audioSourceNode?.disconnect();
    audioGainNode?.disconnect();
    audioSourceNode = null;
    audioGainNode = null;
  };
  pc.addEventListener("connectionstatechange", () => {
    if (
      pc.connectionState === "closed"
      || pc.connectionState === "failed"
      || pc.connectionState === "disconnected"
    ) {
      cleanup();
    }
  });
  pc.addEventListener("iceconnectionstatechange", () => {
    if (
      pc.iceConnectionState === "closed"
      || pc.iceConnectionState === "failed"
      || pc.iceConnectionState === "disconnected"
    ) {
      cleanup();
    }
  });

  pc.addTransceiver("video", { direction: "recvonly" });
  pc.addTransceiver("audio", { direction: "recvonly" });

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const answer = await apiPost<{ sdp: string; type: RTCSdpType }>(
    `/sessions/${sessionId}/webrtc/offer`,
    { sdp: pc.localDescription?.sdp ?? "", type: pc.localDescription?.type ?? "offer" }
  );

  await pc.setRemoteDescription(new RTCSessionDescription(answer));
  ensureVideoPlayback();
  connectWebAudioOutput();
  ensureAudioPlayback?.();
  options.onRemoteStream?.(remoteStream);
  return { pc, remoteStream };
}
