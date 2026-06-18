# Image Deployment

This guide explains how to create an OpenTalking instance from the Compshare image. Use this path when you do not want to install CUDA, PyTorch, OpenTalking, OmniRT, and QuickTalk weights manually.

Image page: [OpenTalking one-click deployment](https://www.compshare.cn/images/TdDwmKZUZebI)

This page is for image users. It does not cover author workflows such as creating a private image, publishing a community image, version upgrades, or promotion links. Users only need to create an instance, open WebUI, fill in runtime configuration, and use real-time conversation or video creation.

## 0. Image contents

The image runs on a cloud Linux environment and already includes:

- OpenTalking WebUI.
- OpenTalking API.
- OmniRT QuickTalk inference service.
- QuickTalk talking-head video driving runtime.
- Edge TTS as the default text-to-speech path.
- DashScope ASR configuration entry.
- Real-time conversation, video creation, asset library, and exported-video management.

Cloud Linux instances cannot directly run Windows bundles or `.exe` files. With this image, you do not need to upload a local Windows package or reinstall PyTorch, CUDA, or QuickTalk weights.

## 1. Register and log in

1. Open the [OpenTalking image page](https://www.compshare.cn/images/TdDwmKZUZebI).
2. Click **Register** or **Console** in the upper-right corner.
3. Complete registration with the account method supported by the platform.
4. After logging in, return to the image page and confirm that the image is **OpenTalking** and the latest version is selected.

## 2. Create a GPU instance

1. Click **Deploy GPU Instance** from the image page, or enter the GPU instance creation page from the console.
2. Select the **OpenTalking** image and the latest version.
3. Choose an available GPU specification. The image targets QuickTalk inference; 3090, RTX 40 series, RTX 50 series, 3080Ti, or higher is recommended.
4. One GPU is usually enough for a single-instance real-time conversation and video creation experience.
5. Keep the default system disk unless you have a specific storage requirement.
6. A data disk is optional. It is useful for private files, but it is not part of the shared image.
7. Pay-as-you-go billing is recommended for trials, because the instance can be shut down when not in use.
8. Set an instance name as needed. It can usually be changed later.
9. Create the instance and wait until its status becomes **running**.

After the instance starts, the image automatically starts OpenTalking Web, OpenTalking API, and OmniRT QuickTalk.

## 3. Enter the instance and terminal

After the instance is running, the instance list usually provides these entries:

- **JupyterLab**: file manager and terminal; use it to check service status, restart services, and inspect logs.
- **SSH / VNC**: remote login.
- **Shutdown**: stop the instance when it is not in use to reduce compute cost.
- **More actions**: common actions include restart, firewall configuration, and image operations.

Open JupyterLab and click **Terminal** to create a terminal window. Run status and restart commands there.

Common commands:

```bash
cd /root/test
ls -hl
df -hl
bash /root/test/start_quicktalk_edge_asr.sh status
```

## 4. Open WebUI

OpenTalking WebUI uses port `5173` by default.

If the platform provides a web entry, open the `WebUI` or `5173` port. If you only have a JupyterLab URL, replace `8888` with `5173` and remove paths such as `/lab`.

Example:

```text
https://<instance-domain>:8888/lab
```

Change it to:

```text
https://<instance-domain>:5173
```

If the page does not open, first confirm that the instance is **running**. If it still cannot be reached, open **Firewall Configuration** from the instance's **More actions** menu and confirm that port `5173` is allowed.

## 5. Configure LLM / TTS / ASR

After opening WebUI for the first time, expand the collapsed **Static Config** section at the top of the real-time conversation settings panel.

Fill in the common runtime settings:

- LLM: base URL, model name, and API key.
- TTS: `edge` is the default keyless option.
- ASR: DashScope ASR requires a DashScope API key. `paraformer-realtime-v2` can be used as the model.

Click **Apply Config** after editing. The keys are saved in the instance environment, and new requests and sessions use the refreshed values. Secret fields are never echoed back; leaving a key input empty keeps the saved key.

Configuration tips:

- Keep TTS as `edge` for the fastest validation path.
- If ASR and LLM use the same DashScope account, enable DashScope key synchronization.
- After changing TTS or ASR providers, restart the current digital-human session.

## 6. Verify services

Run this command in the instance terminal:

```bash
bash /root/test/start_quicktalk_edge_asr.sh status
```

Expected status:

```text
OpenTalking API: running
OpenTalking frontend: running
OmniRT QuickTalk: running
OmniRT /v1/audio2video/models: ok
```

To restart the full stack:

```bash
bash /root/test/start_quicktalk_edge_asr.sh restart
```

You can also stop and start explicitly:

```bash
bash /root/test/start_quicktalk_edge_asr.sh stop
bash /root/test/start_quicktalk_edge_asr.sh start
```

The startup script manages OpenTalking Web, OpenTalking API, and OmniRT QuickTalk together. After an instance restart, if WebUI reports that the model is disconnected, run `restart` and then `status`.

## 7. Use real-time conversation

1. Open WebUI and enter **Real-time Conversation**.
2. Expand **Static Config** and confirm that the LLM and ASR keys are configured.
3. Select an avatar asset.
4. Select `quicktalk` as the driving model.
5. Select `edge` as TTS.
6. Select DashScope as ASR and confirm the model is `paraformer-realtime-v2`.
7. Start the digital human, allow microphone access in the browser, and begin the conversation.

If the browser does not ask for microphone permission, check the permission icon in the address bar and confirm that you are using the WebUI address provided by the platform.

## 8. Use video creation

1. Open **Video Creation**.
2. Select an avatar asset.
3. Choose text-driven or audio-driven generation.
4. Enter the script or upload audio.
5. Submit the task and download the generated result after it finishes.

The image includes QuickTalk and OmniRT, so real-time conversation and video creation use the same inference service for talking-head video driving.

## 9. Shut down when idle

For pay-as-you-go instances, shut down the instance from the instance list when it is not in use. When you need it again, start the instance, wait until it is running, and open WebUI on port `5173`.

If services do not recover automatically after startup, run this in the JupyterLab terminal:

```bash
bash /root/test/start_quicktalk_edge_asr.sh restart
```

## FAQ

**Q1: WebUI does not open. What should I check?**  
**A1:** Confirm that the instance is running and that the platform entry or firewall rule allows port `5173`. If you start from a JupyterLab URL, replace `8888` with `5173` and remove `/lab`.

**Q2: WebUI says the driving model is not connected. What should I do?**  
**A2:** Run:

```bash
bash /root/test/start_quicktalk_edge_asr.sh restart
bash /root/test/start_quicktalk_edge_asr.sh status
```

Confirm that OpenTalking API, OpenTalking frontend, and OmniRT QuickTalk are all `running`, and that `/v1/audio2video/models` is `ok`.

**Q3: ASR does not recognize speech. What should I check?**  
**A3:** Expand **Static Config**, confirm that the DashScope API key is set, and click **Apply Config**. The browser must also allow microphone access for the current page.

**Q4: TTS has no audio. What should I check?**  
**A4:** Use `edge` TTS first and confirm that the browser is not muted. After changing TTS provider, restart the current digital-human session.

**Q5: Do I need to upload a Windows bundle?**  
**A5:** No. This image is already a runnable cloud Linux environment. Windows `.exe` files, local dependency folders, and local paths usually cannot run directly in a cloud Linux instance.

**Q6: Do I need to create a private image or publish a community image?**  
**A6:** No for normal usage. Private-image creation, community-image publishing, and version upgrades are image-author workflows and are not required for deploying and using OpenTalking.
