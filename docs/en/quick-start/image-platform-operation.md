# Image Platform Operation Guide

This guide explains how to use an OpenTalking image after creating an instance on an image platform. It covers access, runtime configuration, real-time conversation, video creation, assets, and basic troubleshooting. It does not cover source development, image building, or image publishing.

## 1. Image Entry Points

The image starts OpenTalking services automatically after the instance boots. In normal use, users do not need to run startup commands manually.

Key entry points:

- Web page port: `5173`
- OpenTalking API port: `8000`
- OmniRT QuickTalk inference port: `9000`
- Autostart script: `/start.d/opentalking.sh`
- Manual management script: `/root/test/start_quicktalk_edge_asr.sh`

The image provides:

- Real-time conversation: QuickTalk / mock
- TTS: Edge / DashScope Qwen
- ASR: DashScope Paraformer
- Video creation: generated results saved as exported videos in the asset library
- Asset library: exported videos, knowledge bases, memory libraries, avatar assets, and voice assets

## 2. Create an Instance and Open the Web Page

1. Create an instance from this image on the image platform.
2. Wait until the instance status becomes running.
3. Confirm that port `5173` is open in the platform firewall or security group.
4. Open the Web page.

If the platform provides a direct public IP address:

```text
http://INSTANCE_PUBLIC_IP:5173
```

If the platform provides a JupyterLab or Notebook URL, copy the current browser URL, replace port `8888` with `5173`, and remove the trailing Jupyter path.

Example:

```text
https://example.com/proxy/8888/lab
```

Change it to:

```text
https://example.com/proxy/5173/
```

## 3. First-Time Configuration

After opening the Web page, expand `Static Config` at the top of the left panel.

If keys are not configured yet, the page will show a setup prompt such as `Needs setup` or `Key not configured`. Fill in the required values and click `Apply Config`.

Required configuration:

- LLM Base URL
- LLM Model
- LLM API Key
- TTS Provider
- Edge Voice, when using Edge TTS
- DashScope TTS Model / Voice / Key, when using Qwen TTS
- STT Model
- DashScope STT Key

Notes:

- Edge TTS does not require an API key.
- DashScope STT requires a DashScope key.
- DashScope Qwen TTS requires a DashScope TTS key.
- If `Sync new DashScope key for LLM / TTS / STT` is enabled, the newly entered DashScope key is written to the corresponding runtime settings.
- Key inputs do not display saved plaintext values.
- After a key has been configured, leaving the input empty keeps the saved key unchanged.
- Configuration is saved to `/root/test/opentalking/.env` in the current image instance. It persists after instance restart, but a newly created instance needs to be configured again.
- Keys, model names, and URLs support hot update. The whole service does not need to restart. If an active real-time session still uses old settings, stop that session and start a new one.

## 4. Real-Time Conversation

1. Open the `Real-time Conversation` page.
2. Select an avatar and wait until the asset is ready.
3. In the left `Driver Model` section, select:
   - `QuickTalk`: real digital-human video driving.
   - `No driver / mock`: validates the LLM, TTS, and ASR chain without real video driving.
4. In the TTS section, select:
   - `Edge`
   - `Qwen`
5. Start the session.
6. Allow microphone access when the browser asks for permission.
7. Use text input, microphone input, or uploaded audio for conversation.
8. To save a result, use recording in the real-time conversation page. After recording finishes, open `Asset Library -> Exported Videos`.

In this image, the real-time conversation page only enables `mock` and `QuickTalk` driver models. Other models are shown as disabled in the frontend.

## 5. Video Creation

1. Switch to `Video Creation` from the top navigation.
2. Select an avatar.
3. Select an audio source:
   - Generate speech from text.
   - Upload audio.
   - Use a configured or cloned voice.
4. Select TTS:
   - Edge TTS works without an API key.
   - DashScope Qwen TTS requires configuration in `Static Config` first.
5. Click generate.
6. After generation succeeds, the page shows that the result has been saved to the asset library.
7. Open `Asset Library -> Exported Videos` to view, play, download, or delete the generated result.

## 6. Asset Library

Open `Asset Library` from the top navigation to use:

- `Exported Videos`: real-time conversation recordings and video creation results.
- `Knowledge Bases`: create knowledge bases, upload documents, rebuild indexes, and delete knowledge bases.
- `Memory Libraries`: create memory libraries, view memory entries, import memory, and delete memory.
- `Avatar Assets` / `Voice Assets`: view available avatars and voices in the image.

All generated video results are saved under `Asset Library -> Exported Videos`.

## 7. Manual Service Management

If the page cannot open, the model is disconnected, or services are unhealthy, run these commands in the image platform terminal.

Check status:

```bash
bash /root/test/start_quicktalk_edge_asr.sh status
```

Restart the full stack:

```bash
bash /root/test/start_quicktalk_edge_asr.sh restart
```

Stop services:

```bash
bash /root/test/start_quicktalk_edge_asr.sh stop
```

The startup script stops old services, clears residual listeners on ports `5173`, `8000`, and `9000`, then starts:

- OpenTalking Web
- OpenTalking API
- OmniRT QuickTalk

## 8. FAQ

Page cannot open:

- Confirm the instance is running.
- Confirm port `5173` is open in the firewall or security group.
- If using a Jupyter URL, confirm that `8888` has been replaced with `5173` and paths such as `/lab` have been removed.
- Run `bash /root/test/start_quicktalk_edge_asr.sh status` in the terminal.

The page says the current driver model is not connected:

- Run `bash /root/test/start_quicktalk_edge_asr.sh restart`.
- Run `status` again and confirm that OmniRT QuickTalk and OpenTalking API are available.

ASR fails:

- Confirm that browser microphone permission is allowed.
- Confirm that DashScope STT Key and STT Model are configured in `Static Config`.
- Restart the current real-time session after changing configuration.

TTS fails:

- Edge TTS does not require a key. Use Edge first to validate the chain.
- When using Qwen TTS, confirm that DashScope TTS Key, Model, and Voice are configured.

Video creation fails:

- Run `status` and confirm that QuickTalk inference is available.
- Confirm that the selected avatar asset is ready.
- Confirm that text input or uploaded audio is not empty.

Check logs:

```bash
tail -80 /root/test/logs/start.d-opentalking.log
tail -80 /root/test/logs/opentalking-api-8000.log
tail -80 /root/test/logs/opentalking-web-5173.log
tail -80 /root/test/logs/omnirt-quicktalk.log
```
