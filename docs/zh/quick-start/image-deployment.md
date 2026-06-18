# 镜像部署

本文介绍如何使用优云智算镜像快速创建 OpenTalking 实例。适合不想从零安装 CUDA、PyTorch、OpenTalking、OmniRT 和 QuickTalk 权重的用户。

镜像地址：[OpenTalking 一键部署](https://www.compshare.cn/images/TdDwmKZUZebI)

本文面向镜像使用者，不覆盖镜像作者的制作、发布、版本升级和推广收益流程。用户只需要创建实例、打开 WebUI、填写运行配置并使用实时对话或视频创作功能。

## 0. 镜像内容

该镜像基于云端 Linux 环境，已经预装并配置好：

- OpenTalking WebUI。
- OpenTalking API。
- OmniRT QuickTalk 推理服务。
- QuickTalk 数字人视频驱动环境。
- Edge TTS 默认语音合成链路。
- DashScope ASR 配置入口。
- 实时对话、视频创作、资产库和导出视频管理能力。

云端 Linux 实例不能直接运行 Windows 整合包或 `.exe` 文件。使用本镜像时不需要上传本地 Windows 一键包，也不需要重新安装 PyTorch、CUDA 或 QuickTalk 权重。

## 1. 注册并登录

1. 打开 [OpenTalking 一键部署镜像](https://www.compshare.cn/images/TdDwmKZUZebI)。
2. 点击页面右上角的 **立即注册** 或 **控制台**。
3. 按平台提示完成手机号、邮箱或第三方账号注册。
4. 登录后回到镜像页面，确认页面标题为 **OpenTalking**，版本为最新版本。

## 2. 创建 GPU 实例

1. 在镜像页面点击 **部署 GPU 实例** 或从控制台进入 GPU 实例创建页。
2. 镜像选择 **OpenTalking**，版本选择最新版本。
3. 选择可用 GPU 规格。该镜像面向 QuickTalk 推理，建议选择 3090、RTX 40 系、RTX 50 系、3080Ti 或更高规格。
4. GPU 数量通常选择 1 张即可。实时对话和视频创作的单实例体验不需要多卡同步。
5. 系统盘保持平台默认配置即可；如平台提供 200GB 免费系统盘，通常不需要额外扩大。
6. 数据盘默认可不挂载。数据盘适合保存私有文件，但不会随镜像发布或复制给其他用户。
7. 计费方式建议选择按量计费，便于不用时关机节省费用。
8. 实例名称按需填写，后续也可以修改。
9. 创建实例并等待状态变为 **运行中**。

创建完成后，镜像会自动启动 OpenTalking Web、OpenTalking API 和 OmniRT QuickTalk 推理服务。

## 3. 进入实例和终端

实例运行后，实例列表通常会提供几个入口：

- **JupyterLab**：进入文件管理器和终端，适合执行状态检查、重启脚本、查看日志。
- **SSH / VNC**：用于远程登录实例。
- **关机**：不用实例时可以关机，避免继续产生计算费用。
- **更多操作**：常见入口包括重启实例、配置防火墙、制作镜像等。

进入 JupyterLab 后，点击 **终端** 新建一个终端窗口。后续状态检查和重启命令都在这个终端里执行。

常用命令：

```bash
cd /root/test
ls -hl
df -hl
bash /root/test/start_quicktalk_edge_asr.sh status
```

## 4. 打开 WebUI

OpenTalking WebUI 默认使用 `5173` 端口。

如果平台提供 Web 访问入口，选择 `WebUI` 或 `5173` 端口打开即可。如果只有 JupyterLab 地址，可以把地址中的 `8888` 改成 `5173`，并删除 `/lab` 等路径。

示例：

```text
https://<instance-domain>:8888/lab
```

改为：

```text
https://<instance-domain>:5173
```

如果页面打不开，先确认实例状态为 **运行中**。如果仍无法访问，在实例列表的 **更多操作** 中进入 **配置防火墙**，确认已开放 `5173` 端口。

## 5. 配置 LLM / TTS / ASR

首次进入 WebUI 后，实时对话左侧设置面板顶部有默认收起的 **静态配置** 区域。

展开后填写常见运行配置：

- LLM：填写 Base URL、模型名和 API Key。
- TTS：默认可以使用 `edge`，不需要 API Key。
- ASR：DashScope ASR 需要填写 DashScope API Key，模型可使用 `paraformer-realtime-v2`。

填写后点击 **应用配置**。Key 会保存到实例环境中，后续新请求和新会话会使用新的配置。Key 输入框不会回显；如果已经配置过，留空表示保留当前 Key。

配置建议：

- 如果只想快速验证语音合成，TTS 保持 `edge`。
- 如果 ASR 或 LLM 使用同一个百炼账号，可以勾选同步 DashScope Key。
- 修改 TTS 或 ASR provider 后，建议重新启动当前数字人会话。

## 6. 验证服务状态

在实例终端执行：

```bash
bash /root/test/start_quicktalk_edge_asr.sh status
```

正常情况下应看到：

```text
OpenTalking API: running
OpenTalking frontend: running
OmniRT QuickTalk: running
OmniRT /v1/audio2video/models: ok
```

如果需要重启整套服务：

```bash
bash /root/test/start_quicktalk_edge_asr.sh restart
```

也可以分别执行：

```bash
bash /root/test/start_quicktalk_edge_asr.sh stop
bash /root/test/start_quicktalk_edge_asr.sh start
```

该启动脚本会统一管理镜像内的 OpenTalking Web、OpenTalking API 和 OmniRT QuickTalk 服务。实例重启后，如果页面提示模型未连接，优先执行 `restart` 和 `status`。

## 7. 使用实时对话

1. 打开 WebUI 后进入 **实时对话**。
2. 展开 **静态配置**，确认 LLM 和 ASR Key 已配置。
3. 选择数字人资产。
4. 驱动模型选择 `quicktalk`。
5. TTS 选择 `edge`。
6. ASR 选择 DashScope，并确认模型名为 `paraformer-realtime-v2`。
7. 点击启动数字人，浏览器授权麦克风后开始对话。

如果浏览器没有弹出麦克风授权，检查浏览器地址栏权限设置，并确认当前访问地址是平台提供的 WebUI 地址。

## 8. 使用视频创作

1. 进入 **视频创作** 页面。
2. 选择数字人资产。
3. 选择文本驱动或音频驱动。
4. 填写文案或上传音频。
5. 提交任务，等待生成完成后下载结果。

该镜像已预装 QuickTalk 和 OmniRT，实时对话与视频创作都会通过同一套推理服务完成数字人视频驱动。

## 9. 不用时关机

按量计费实例在不用时建议从实例列表执行 **关机**。再次使用时开机，等待实例变为运行中，然后打开 `5173` 端口访问 WebUI。

如果开机后服务没有自动恢复，在 JupyterLab 终端执行：

```bash
bash /root/test/start_quicktalk_edge_asr.sh restart
```

## 常见问题

**Q1：页面打不开怎么办？**  
**A1：** 确认实例状态为运行中，并确认平台访问入口或防火墙规则已开放 `5173` 端口。如果从 JupyterLab 地址进入，请把 `8888` 改成 `5173`，并删除 `/lab`。

**Q2：页面提示“当前驱动模型未连接”怎么办？**  
**A2：** 在实例终端执行：

```bash
bash /root/test/start_quicktalk_edge_asr.sh restart
bash /root/test/start_quicktalk_edge_asr.sh status
```

确认 OpenTalking API、OpenTalking frontend、OmniRT QuickTalk 都是 `running`，并且 `/v1/audio2video/models` 显示 `ok`。

**Q3：ASR 不能识别语音怎么办？**  
**A3：** 展开 **静态配置**，确认 DashScope API Key 已填写并点击 **应用配置**。浏览器也需要允许当前页面访问麦克风。

**Q4：TTS 没有声音怎么办？**  
**A4：** 优先选择 `edge` TTS，并确认浏览器没有静音。切换 TTS provider 后建议重新启动当前数字人会话。

**Q5：是否需要上传 Windows 整合包？**  
**A5：** 不需要。该镜像已经是可运行的云端 Linux 环境。Windows 整合包中的 `.exe`、本地依赖目录和本地路径通常不能直接在云端 Linux 实例中运行。

**Q6：是否需要自己制作私有镜像或发布社区镜像？**  
**A6：** 普通使用者不需要。制作私有镜像、发布社区镜像和版本升级是镜像作者流程，不影响直接部署和使用 OpenTalking。
