<p align="center">
  <img src="logo.png" alt="RhythmAlign Logo" width="140" />
</p>

<h1 align="center">RhythmAlign</h1>

<p align="center">
  <strong>一键将你的音游手元对齐到录音室级原声音轨。</strong><br>
  二级 Chroma/Onset 级联对齐 &bull; Z-score 可靠性门控 &bull; VFR 加固的 ffmpeg 导出管线。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="Platform" />
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs" />
</p>

<p align="center">
  <img src="screenshot.png" alt="RhythmAlign 主界面截图" width="720" />
</p>

<p align="center">
  <b>简体中文说明</b> &nbsp;|&nbsp; <a href="README.md">English Readme</a>
</p>

---

## ⚠️ 免责声明

本软件**完全免费开源**，基于 MIT License 分发，仅供个人非商业用途。若您是通过付费渠道获得，请立即申请退款。

RhythmAlign 是独立的社区工具，**与 lowiro 无任何关联、背书或合作关系**。所有节奏游戏相关名称的出现仅为兼容性描述用途。

---

## 这个工具解决什么问题？

你在桌面上架好手机，开启录像——机载麦克风录下的是键盘敲击的噼啪声和房间的混响。与此同时，你手上还有一份录音室品质的原声音轨：干净、无压缩、完美混音。

现在你需要**把相机里那轨嘈杂的音频替换成录音室原声**，而且两段音频必须在几十毫秒的精度内对齐。在剪辑软件里手动拖动音轨，一个视频就要折腾好几分钟，还永远对不齐。

RhythmAlign 能做到的是：**自动分析，秒出结果，附带置信度评分**。它在音乐特征空间中对两条音轨做互相关，找到亚秒级的时间偏移量，然后直接封装输出 MP4——视频流原样保留，画质零损失。

如果你玩 *Arcaea*、*Phigros*、*osu!*、*maimai*、*CHUNITHM* 或任何其他音游并制作手元内容，这就是你需要的工具。

---

## ✨ 功能特性

- **一键导出** — 选视频，选纯音频，选保存路径，搞定。输出的 MP4 中，视频流原封不动，音轨已对齐并混音。
- **视频流直拷** — 视频比特流 1:1 拷贝，零重新编码。3 分钟的视频导出不到 10 秒、画质无任何折损。
- **硬件编码回退** — 需要转码时，可选 NVIDIA NVENC 加速，支持 6000k / 10000k / 20000k 三档码率预设。
- **音量预设** — 一键 *街机* / *手机* / *桌面* 增益方案，针对常见录制场景调优。当然你也可以手动拖滑块微调。
- **纯分析模式** — 只计算偏移量，不渲染导出。把数值直接填进 DaVinci Resolve、Premiere 或任何剪辑软件的时间轴即可。
- **手动偏移微调** — ±500 ms 滑块，应对源音频严重降质的极端情况。
- **内置诊断工具** — `diagnose_offset.py` 可逐项输出 Chroma 特征方差、互相关 Z-score、音轨元数据，帮助排查顽固文件对。
- **完整中英双语界面** — 英文 / 简体中文随时切换，语言偏好自动持久化，基于 JSON 的 i18n 引擎无任何框架依赖。

---

## 🔬 核心架构 — 二级特征级联

对齐问题的精确数学表述是：*给定两条音色、响度、噪声剖面截然不同的音频信号，找到使它们音乐内容重合度最大化的时间偏移量。*

直接对原始波形做互相关在这里毫无意义——两者的波形在结构上完全不同。RhythmAlign 在**音乐特征空间**中操作，将音色和录音设备特征统一剥离。

### 第一级 — Chroma CENS（和声指纹）

```python
feat_video = librosa.feature.chroma_cens(y=y_video, sr=sr, hop_length=512)
feat_music = librosa.feature.chroma_cens(y=y_music, sr=sr, hop_length=512)
```

**Chroma CENS**（Chroma Energy Normalized Statistics，色度能量归一化统计）将音频压缩为每帧 12 维音高类别向量，再经过时序平滑与 L¹ 归一化。最终得到的是一份**不受音色影响的音高指纹**：它只关心哪些音高在响，而完全不关心这些声音是通过录音棚电容麦录的、还是手机贴在桌上录的。

对 12 个色度通道分别做互相关后求和，得到置信度曲线：

```python
correlation = np.zeros(feat_video.shape[1] + feat_music.shape[1] - 1)
for i in range(12):
    correlation += signal.correlate(feat_music[i], feat_video[i], mode='full', method='fft')
lag = np.argmax(correlation) - (feat_video.shape[-1] - 1)
offset = -(lag * hop_length) / sr
```

这条策略在干净的录制（桌面内录、采集卡线路输入）下表现出色。但当房间混响和环境噪声将和声剖面淹没时——这正是手机外录街机手元的典型场景——Chroma 特征的可靠性就会下降。

### 第二级 — Onset Strength Envelope（节奏回退）

当第一级返回弱峰值时，管线自动切换到**起始强度包络**：

```python
onset_video = librosa.onset.onset_strength(y=y_video, sr=sr, hop_length=512)
onset_music = librosa.onset.onset_strength(y=y_music, sr=sr, hop_length=512)
correlation = signal.correlate(onset_music, onset_video, mode='full', method='fft')
```

起始强度是每轨**一维信号**，捕捉的是音符的瞬态起始——*何时*开始，而不是*什么音*在响。这使其对噪声和失真具有极强的鲁棒性。即便是一段严重削波的手机录音，也能保留音乐节奏的瞬态结构。

代价是对齐精度低于 Color 级（起始帧远稀疏于色度帧），但作为回退方案，它能将一堆不可用噪声转化为有效结果。

---

## 🛡️ 可靠性门控 — 杜绝"悄悄对歪了"

自动对齐工具最危险的失败模式是：**在用户完全不知情的前提下，产出一个错误的偏移量**。RhythmAlign 对每次相关结果强制进行统计置信度检验：

```python
z_score = (np.max(correlation) - np.mean(correlation)) / np.std(correlation)
_CONFIDENCE_THRESHOLD = 2.0  # 经验标定值
```

Z-score 衡量的是相关峰值超出噪声基底多少个标准差：

| Z-score | 含义 | 行为 |
|---|---|---|
| **< 1.0** | 纯随机噪声，无可辨识峰值 | 两级均失败，错误上抛至 UI |
| **1.0 – 2.0** | 弱峰值，结果可能不可靠 | 回退至第二级；若均失败，错误上抛 |
| **> 2.0** | 清晰、无歧义的峰值 | 接受结果，继续导出 |

当两级策略均未通过 Z-score 门控时，工具抛出 `CorrelationLowConfidenceError`，附带实际的 Z-score 值与阈值。UI 会给出明确指引——使用手动偏移滑块，或尝试更清晰的音频源。**关键在于：宁可拒绝导出，也绝不静默地输出一个对歪了的视频**。

---

## 🎬 FFmpeg 管线 — VFR 漂移消除与 QuickTime 元数据消毒

手机录制的视频存在两个会破坏简单 ffmpeg 管线的结构性问题：

1. **可变帧率（VFR）** — 视频帧时间戳不均匀。在未显式标注的情况下，ffmpeg 无法在 VFR 输入上维持音画同步。
2. **QuickTime Edit-List 元数据原子** — Apple MOV 容器内嵌编辑列表，指示播放器进行非平凡的时间线变换（旋转、裁剪、轨重排）。ffmpeg 可能遵守也可能忽略——行为因编译版本和运行平台而异。

RhythmAlign 的导出命令对这两个问题进行了强力反制：

```bash
ffmpeg -y \
  -fflags +genpts \
  -avoid_negative_ts make_zero \
  -i video.mp4 \
  -i music.mp3 \
  -filter_complex "[0:a:0]volume=${vol_orig}[a0];[1:a:0]${music_filter}[a1];[a0][a1]amix=inputs=2:duration=first[aout]" \
  -map 0:v:0 -map "[aout]" \
  -c:v copy \
  -c:a aac -b:a 320k \
  -map_metadata -1 \
  -movflags +faststart \
  output.mp4
```

每个 flag 都有明确意图：

| Flag | 作用 |
|---|---|
| `-fflags +genpts` | 从解码顺序强制重建显示时间戳——消除 VFR 带来的音画漂移 |
| `-avoid_negative_ts make_zero` | 将所有负时间戳规整化到零——防止不同播放器产生不一致的 A/V 偏移 |
| `-c:v copy` | 视频流无损拷贝——零编码代际损失，典型视频导出不到 10 秒 |
| `-map_metadata -1` | 剥离全部源文件私有元数据——移除 QuickTime 编辑列表、旋转矩阵、色彩配置文件 |
| `-movflags +faststart` | 将 moov 原子前置到文件头部——支持流式播放，无需等待完整下载 |

Python 层还处理了若干边界情况：

- **视频无音轨**：通过 `ffprobe -select_streams a` 探测，自动跳过 amix 混音滤镜，纯音乐轨直接作为音频源。
- **负偏移量**（音乐比视频先开始）：使用 `atrim=start=N` 裁剪音乐轨，而非用数字静音填充。
- **时长解析失败**：从 `ffmpeg -i` 正则匹配回退到 `ffprobe -show_entries format=duration` JSON 探测；两者均失败时抛出明确 `RuntimeError`。
- **临时 WAV 文件残留**：无论函数以何种路径退出，`finally` 块始终执行清理。

---

## 🚀 快速开始

### 环境要求

- **Windows 10 或 11**（主要目标平台；核心引擎是跨平台的，macOS/Linux 未测试）
- **Python 3.9+**（64 位）
- **FFmpeg** 通过 `imageio-ffmpeg` 自动捆绑——无需单独安装

### 安装

```bash
git clone https://github.com/Daozhu1007/RhythmAlign.git
cd RhythmAlign
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 运行

```bash
python ui_main.py
```

### 诊断顽固文件对

```bash
python diagnose_offset.py "D:\videos\handcam.mp4" "D:\music\track.mp3"
```

脚本输出涵盖：音频编码 + 采样率、RMS/峰值能量（侦测静音轨道）、Chroma 特征方差（侦测无特征音频）、互相关 Z-score 与峰值均值比、以及针对每项指标的具体排错建议。

---

## 📖 使用指南

### 自动对齐标签页

1. 选择你的**视频**（MP4 / MKV / MOV / AVI / FLV / WMV / WebM / TS）。
2. 选择你的**纯音频**（MP3 / WAV / FLAC / M4A / AAC / OGG / WMA）。
3. 轻触音量预设——*街机*（键盘声大）、*手机*（环境安静）、*桌面*（系统内录）——或手动拖滑块调节。
4. 点击**完整导出**，选择输出路径。
5. 完成。输出的 MP4 包含原封不动的视频流和已同步混音的音轨。

### 纯分析标签页

当你只需要偏移量数值而不需要渲染时使用——比如习惯在自己剪辑软件（DaVinci Resolve / Premiere）中完成混音的场景。

结果卡会显示类似 `+0.1234 s` 或 `-0.5678 s` 的精确偏移量，并附带文字说明：在时间轴上向哪个方向拖动纯音乐轨。

---

## ⚙️ 设置项

所有设置持久化保存在 `config.json`。在设置标签页中修改：

| 设置项 | 默认值 | 效果 |
|---|---|---|
| **界面语言** | 简体中文 | English / 中文界面；需重启生效 |
| **视频流直拷** | 开 | 跳过视频重编码，近乎瞬时导出，零画质损失 |
| **GPU 加速渲染** | 关 | NVIDIA NVENC 编码（仅在关闭流直拷时生效） |
| **视频码率** | 10000k | 6000k（分享） / 10000k（推荐） / 20000k（存档） |
| **完成后打开文件夹** | 开 | 导出完成后自动打开目标文件夹 |

---

## 📁 项目结构

```
RhythmAlign/
├── ui_main.py              # PyQt6 + QFluentWidgets GUI（四个标签页：对齐、分析、关于、设置）
├── auto_sync.py            # 核心对齐引擎 + ffmpeg 导出管线
├── diagnose_offset.py      # 命令行诊断工具：Chroma 方差、Z-score、音轨元数据
├── locales/
│   ├── zh_CN.json          # 简体中文字符串表
│   └── en_US.json          # 英文字符串表
├── requirements.txt        # Python 依赖（无 moviepy）
├── logo.png                # 应用图标 — 对立鸭
├── logo.ico                # Windows .ico 版本
└── config.json             # 用户设置（程序自动生成）
```

---

## 🤝 参与贡献

欢迎提交 PR。非平凡改动请先开 Issue 讨论。

当前最需要帮助的方向：
- **macOS / Linux 适配验证** — 核心引擎无任何 Windows 专属依赖；GUI 是跨平台的瓶颈所在
- **额外对齐策略** — MFCC、DTW 或深度学习嵌入作为极端噪声下的第三级回退
- **新语言翻译文件** — i18n 系统无需改代码，直接添加 `locales/ja_JP.json` 即可

---

## 📜 许可与致谢

### 代码许可

MIT License。详见 [LICENSE](LICENSE)。

### 应用图标与品牌素材 — 对立鸭

应用图标及相关视觉素材裁剪自 **"对立鸭"** 表情包系列。该系列素材的使用授权，由以下作者在约稿方协助下慷慨提供免费开源许可：

> **春也Haruya**（[B站 UID: 3280](https://space.bilibili.com/3280)）—— 画师，表情包系列原创作者。
>
> 特别感谢约稿方协商并授予开源使用授权。

### 角色与知识产权

**对立（Tairitsu）** 及相关角色设计、名称、知识产权归 **lowiro** 独占所有。RhythmAlign 为独立、非商业的开源社区工具，与 lowiro 无任何背书、关联或合作关系。

### 合理使用

- 本工具为**免费软件**。若您付费获取，请立即要求退款。
- **仅供个人、非商业用途**。禁止用于盈利，或与商业产品捆绑分发。

---

## 💬 社区

<p align="center">
  <a href="https://github.com/Daozhu1007/RhythmAlign"><img src="github.png" height="24" /></a>
  &nbsp;&nbsp;
  <a href="https://space.bilibili.com/477852567"><img src="bilibili.png" height="24" /></a>
</p>

<p align="center">
  <sub>为音游社区构建。欢迎提交 PR 与 Bug 报告。</sub>
</p>
