# 镜像平台操作文档

本文说明用户在镜像平台创建 OpenTalking 实例后的访问、配置和使用流程，不包含源码开发、镜像制作或发布流程。

## 1. 镜像入口

镜像启动后会自动拉起 OpenTalking 服务。正常情况下，用户不需要手动运行启动命令。

关键入口：

- Web 页面端口：`5173`
- OpenTalking API 端口：`8000`
- OmniRT QuickTalk 推理端口：`9000`
- 自启动脚本：`/start.d/opentalking.sh`
- 手动管理脚本：`/root/test/start_quicktalk_edge_asr.sh`

当前镜像默认提供：

- 实时对话：QuickTalk / mock
- TTS：Edge / DashScope Qwen
- ASR：DashScope Paraformer
- 视频创作：生成结果保存到资产库的导出视频
- 资产库：查看、下载、删除导出视频，并管理知识库和记忆库

## 2. 创建实例并访问页面

1. 在镜像平台选择该镜像创建实例。
2. 等待实例状态变为运行中。
3. 在实例防火墙或安全组里确认端口 `5173` 已开放。
4. 打开 Web 页面。

如果平台直接提供公网地址：

```text
http://实例公网地址:5173
```

如果平台提供 JupyterLab / Notebook 地址，复制当前浏览器地址，把端口 `8888` 改为 `5173`，并去掉后面的 Jupyter 路径。

示例：

```text
https://example.com/proxy/8888/lab
```

改成：

```text
https://example.com/proxy/5173/
```

## 3. 首次配置

首次进入页面后，左侧最上方是默认收起的 `静态配置`。

如果 Key 还没有配置，页面会显示 `需展开配置` 或 `Key 未配置`。展开 `静态配置` 后填写需要的参数，再点击 `应用配置`。

需要配置的内容：

- LLM Base URL
- LLM Model
- LLM API Key
- TTS Provider
- Edge Voice，使用 Edge TTS 时选择
- DashScope TTS Model / Voice / Key，使用 Qwen TTS 时填写
- STT Model
- DashScope STT Key

说明：

- Edge TTS 不需要 API Key。
- DashScope STT 需要 DashScope Key。
- 使用 DashScope Qwen TTS 时需要 DashScope TTS Key。
- 勾选 `新填写的百炼 Key 同步用于 LLM / TTS / STT` 后，本次填写的百炼 Key 会同步写入对应配置。
- Key 输入框不会回显明文。
- 已配置过 Key 后，输入框留空表示保留当前 Key。
- 配置会保存到当前镜像实例的 `/root/test/opentalking/.env`，实例重启后仍然保留；重新创建新实例需要重新配置。
- Key、Model、URL 支持热更新，不需要重启整个服务。已经启动的实时会话如仍使用旧效果，停止会话后重新开始。

## 4. 实时对话

1. 进入 `实时对话` 页面。
2. 选择数字人形象，等待资产状态准备完成。
3. 在左侧 `驱动模型` 选择：
   - `QuickTalk`：真实数字人视频驱动。
   - `无驱动模式/mock`：只验证 LLM、TTS、ASR 链路。
4. 在左侧语音合成区域选择：
   - `Edge`
   - `Qwen`
5. 点击开始会话。
6. 浏览器请求麦克风权限时选择允许。
7. 通过文本输入、麦克风语音输入或上传音频进行对话。
8. 需要保存结果时，在实时对话页使用录制能力；录制完成后到 `资产库 -> 导出视频` 查看。

当前镜像的实时对话页只开放 `mock` 和 `QuickTalk` 驱动模型，其它模型在前端会显示为不可选。

## 5. 视频创作

1. 顶部切换到 `视频创作`。
2. 选择数字人形象。
3. 选择音频来源：
   - 输入文本生成语音。
   - 上传音频。
   - 使用已配置或复刻的音色。
4. 选择 TTS：
   - Edge TTS 可直接使用。
   - DashScope Qwen TTS 需要先在 `静态配置` 中配置 Key。
5. 点击生成。
6. 生成成功后，页面会提示已保存到资产库。
7. 到 `资产库 -> 导出视频` 查看、播放、下载或删除生成结果。

## 6. 资产库

顶部切换到 `资产库` 后可以使用：

- `导出视频`：查看实时对话录制和视频创作生成结果。
- `知识库`：创建知识库、上传文档、重建索引、删除知识库。
- `记忆库`：创建记忆库、查看记忆条目、导入或删除记忆。
- `Avatar资产` / `声音资产`：查看当前镜像内可用的数字人和音色资产。

所有生成类结果统一以视频形式进入 `资产库 -> 导出视频`。

## 7. 手动管理服务

服务异常时，在镜像平台终端执行以下命令。

查看状态：

```bash
bash /root/test/start_quicktalk_edge_asr.sh status
```

重启整套服务：

```bash
bash /root/test/start_quicktalk_edge_asr.sh restart
```

停止服务：

```bash
bash /root/test/start_quicktalk_edge_asr.sh stop
```

启动脚本会先停止旧服务，并清理 `5173`、`8000`、`9000` 端口上的残留进程，再启动：

- OpenTalking Web
- OpenTalking API
- OmniRT QuickTalk

## 8. 常见问题

页面打不开：

- 确认实例处于运行中。
- 确认防火墙或安全组开放 `5173`。
- 如果使用 Jupyter 地址访问，确认已经把 `8888` 改为 `5173`，并去掉 `/lab` 等路径。
- 在终端执行 `bash /root/test/start_quicktalk_edge_asr.sh status` 查看服务状态。

页面提示当前驱动模型未连接：

- 在终端执行 `bash /root/test/start_quicktalk_edge_asr.sh restart`。
- 重启后再次执行 `status`，确认 OmniRT QuickTalk 和 OpenTalking API 均可用。

ASR 语音识别失败：

- 确认浏览器麦克风权限已允许。
- 确认 `静态配置` 里的 DashScope STT Key 和 STT Model 已填写。
- 修改配置后重新开始当前实时会话。

TTS 语音合成失败：

- Edge TTS 不需要 Key，优先用 Edge 验证链路。
- 使用 Qwen TTS 时，确认 DashScope TTS Key、Model 和 Voice 已配置。

视频创作失败：

- 先执行 `status` 确认 QuickTalk 推理服务可用。
- 确认数字人形象资产已准备完成。
- 确认输入文本或上传音频不为空。

查看日志：

```bash
tail -80 /root/test/logs/start.d-opentalking.log
tail -80 /root/test/logs/opentalking-api-8000.log
tail -80 /root/test/logs/opentalking-web-5173.log
tail -80 /root/test/logs/omnirt-quicktalk.log
```
