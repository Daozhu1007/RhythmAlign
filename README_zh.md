<p align="center">
  <img src="logo.png" alt="RhythmAlign Logo" width="128" />
</p>

<h1 align="center">RhythmAlign</h1>
<p align="center">
  <strong>为音游手元视频打造的工业级音画自动对齐工具。</strong><br>
  二级特征级联 &bull; 可靠性门控 &bull; VFR 稳定的 ffmpeg 渲染管线。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python" />
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey" alt="Platform" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
  <img src="https://img.shields.io/badge/status-stable-brightgreen" alt="Status" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome" />
</p>

<p align="center">
  <img src="screenshot.png" alt="RhythmAlign 主界面" width="720" />
</p>

---

## RhythmAlign 是什么？

RhythmAlign 为音游玩家和内容创作者解决一个真实且棘手的问题：**将手元录像与高品质纯音频自动对齐**，使键盘敲击、画面与音乐完美同步——即使你的视频来自手机外录、可变帧率（VFR），甚至是 iPhone 的 QuickTime 封装格式。

如果你在游玩 *Arcaea*、*Phigros*、*osu!*、*maimai* 或任何其他音游并制作手元内容，你一定经历过这种痛苦：在一台设备上录制游戏画面，想把嘈杂的室内录音替换为录音室级别的原声音轨，然后在剪辑软件里手动一点点拖动对齐，既枯燥又不精确。RhythmAlign 用一套**数学上严谨、工程上抗造**的信号处理管线，将这个过程完全自动化。

---

## 核心特性

- **一键自动对齐** — 拖入视频 + 纯音频，几秒内输出完美混音、同步的 MP4。
- **两级特征级联策略** — Chroma CENS（音高/和声特征）作为主策略；Onset Strength Envelope（节奏/瞬态特征）作为抗噪回退方案。
- **可靠性门控** — 对互相关峰值进行 Z-score 阈值检验，弱匹配结果会被拦截并报错，杜绝"悄悄对齐歪了"的尴尬。
- **视频流直拷模式** — 直接复刻原始视频流（零画质损失、近乎瞬时的导出速度），仅替换音轨。
- **硬件编码回退** — 需要重编码时，可选 NVIDIA NVENC 加速，支持多档码率预设。
- **VFR / QuickTime 防护** — 强制重生成 PTS 时间戳（`+genpts`）、规整化负时间戳（`make_zero`）、剥离私有 MOV/QuickTime 元数据原子、使用 `+faststart` 优化网页端播放。
- **内置诊断工具** — `diagnose_offset.py` 可分析 Chroma 特征方差、相关度 Z-score、音轨元数据，帮助定位顽固文件对的失败原因。
- **深色 Fluent Design 界面** — 基于 PyQt6 + QFluentWidgets，完整的中英双语国际化支持。

---

## 技术深潜

### 两级特征级联

核心对齐问题的数学表述是：*给定两个音色差异可能极大的音频信号（机载麦克风 vs. 录音室母带），找到使它们的音乐内容重合度最大化的时间偏移量。*

直接对原始波形做互相关在这里是行不通的——两者的波形结构本质不同。RhythmAlign 在**特征空间**中操作：

#### 第一级 — Chroma CENS（和声指纹）

```python
feat = librosa.feature.chroma_cens(y, sr=sr, hop_length=512)
```

**Chroma CENS**（Chroma Energy Normalized Statistics，色度能量归一化统计）将音频映射为每帧 12 维的音高类别分布，然后进行时序平滑与归一化。这个过程剥离了音色、响度、录音设备特征——剩下的是一份鲁棒的**和声指纹**：记录了"哪些音符在响"，而不关心它们*是怎么被录到的*。

对 12 个色度通道分别计算互相关后求和，得到一个相关度向量，其峰值位置即为时间偏移量：

```python
for i in range(12):
    correlation += signal.correlate(feat_music[i], feat_video[i], mode='full', method='fft')
offset = - (argmax(correlation) - (len(feat_video) - 1)) * hop_length / sr
```

这对高质量的录音（如桌面录屏内录的系统音频）效果极佳。但当视频音轨是嘈杂房间里的外录麦克风时——这在手机/街机手元中非常常见——色度特征会被混响和环境噪声破坏。

#### 第二级 — Onset Strength Envelope（节奏回退）

当 Chroma CENS 的结果不可靠时，管线自动切换到**起始强度包络**：

```python
onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
```

起始强度捕捉的是音符*何时开始*——即瞬态攻击——而不是*哪些音符*在响。这是一个每轨一维的信号，使其对噪声和音色失真具有极强的鲁棒性。即使是一个严重削波的手机录音，也能保留音乐的节奏瞬态结构。

然后对两条起始包络进行同样的 FFT 互相关。代价是精度略低于色度特征（起始点比色度帧稀疏），但换来了极高的抗噪能力。

### 可靠性门控 — Z-score 阈值检验

任何自动对齐工具的一个关键失败模式是：**在用户不知情的情况下，产出一个错误的偏移量**。为防止这种情况，RhythmAlign 采用统计可靠性门控：

```python
z_score = (max(correlation) - mean(correlation)) / std(correlation)
if z_score < 2.0:  # 默认阈值
    raise CorrelationLowConfidenceError(z_score, threshold)
```

这个 Z-score 衡量相关峰值高出噪声基底多少个标准差。根据经验：
- **Z < 1.0**：纯随机噪声——没有可辨识的峰值
- **Z = 1.0–2.0**：弱峰值——结果可能不可靠，建议人工验证
- **Z > 2.0**：清晰、无歧义的峰值——结果可信

当两级策略均未通过 Z-score 门控时，工具会明确报告失败，而不是悄悄输出一个错位的视频。用户随后可使用手动偏移滑块，或提供更清晰的音频源。

### FFmpeg 管线 — VFR 漂移消除与元数据消毒

手机录制的视频（尤其是 iPhone）存在两个臭名昭著的问题：

1. **可变帧率（VFR）**——视频轨的时间戳不均匀。当 ffmpeg 处理 VFR 输入时，音视频同步可能随时间漂移。
2. **QuickTime Edit-List 元数据原子**——Apple 设备在 MOV 容器中存储了一个编辑列表，指示播放器进行时间线变换。ffmpeg 可能会、也可能不会遵循这个列表，导致不可预测的 A/V 偏移。

RhythmAlign 的导出管线对这两个问题进行了强力反制：

```bash
ffmpeg -y \
  -fflags +genpts \             # 强制重新生成显示时间戳（修复 VFR）
  -avoid_negative_ts make_zero \ # 将所有负时间戳规整化到零
  -i video.mp4 \
  -i music.mp3 \
  -filter_complex "..." \
  -map 0:v:0 -map [aout] \
  -c:v copy \                   # 视频流直拷：零重编码，零画质损失
  -c:a aac -b:a 320k \
  -map_metadata -1 \            # 剥离所有源文件私有元数据（包括 QuickTime 原子）
  -movflags +faststart \        # 将 moov 原子前置，优化流式播放
  output.mp4
```

其中 `-map_metadata -1` 尤为重要：它剥离了 QuickTime 的私有元数据（旋转矩阵、编辑列表、色彩配置文件），这些数据在不同播放器上可能导致不一致的行为。配合 `+genpts`，输出的 MP4 拥有干净、确定性的时间线，在所有播放器上表现一致。

视频流直拷路径（`-c:v copy`）原样保留视频比特流——零编码代际损失，处理速度极快（通常 3 分钟视频不到 10 秒）。对于需要重编码的用户（如启用硬件编码或更改分辨率），重编码路径支持 NVIDIA NVENC，并带有可配置的码率预设。

### 已处理的边界情况

| 场景 | 行为 |
|---|---|
| 视频无音轨 | 通过 ffprobe 检测；音乐轨作为唯一音频源 |
| 偏移量为负（音乐在视频之前开始） | 使用 `atrim=start=N` 裁剪音乐轨，而非用静音填充 |
| ffmpeg 无法解析时长 | 回退到 ffprobe JSON 探测；若均失败则抛出明确错误 |
| 两级对齐均失败 | 抛出 `CorrelationLowConfidenceError`，并在 UI 中给出可操作的指导 |
| 崩溃时残留临时文件 | 在 `finally` 块中无条件清理，无论退出路径如何 |

---

## 快速开始

### 环境要求

- **Windows 10 或 11**（主要目标平台；Linux/macOS 稍作调整亦可运行）
- **Python 3.9+**（推荐 64 位）
- **FFmpeg** 通过 `imageio-ffmpeg` 自动捆绑——无需手动安装

### 安装

```bash
# 克隆仓库
git clone https://github.com/Daozhu1007/RhythmAlign.git
cd RhythmAlign

# 创建并激活虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux / macOS

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
python ui_main.py
```

### 诊断工具（用于调试顽固文件对）

```bash
python diagnose_offset.py "path/to/video.mp4" "path/to/music.mp3"
```

诊断脚本会输出：
- 音频流编码、声道数、采样率
- RMS 能量和峰值幅度（检测静音/损坏的音轨）
- Chroma CENS 特征方差（检测无特征音频）
- 互相关质量指标（Z-score、峰值均值比）
- 可操作的排查建议

---

## 使用指南

### 自动对齐标签页

1. 选择你的**视频文件**（支持 MP4、MKV、MOV、AVI、FLV、WMV、WebM、TS）。
2. 选择你的**纯音频文件**（支持 MP3、WAV、FLAC、M4A、AAC、OGG、WMA）。
3. （可选）选择**音量预设**——*街机*、*手机*或*桌面*——或手动调整滑块。
4. 点击**完整导出**，选择输出路径。
5. 完成——导出的 MP4 包含原始视频流 + 已同步混音的音轨。

### 纯分析标签页

如果你更习惯在自己的剪辑软件（DaVinci Resolve、Premiere 等）中完成混音，可以使用"纯分析"标签页。它会计算出偏移量，并精确显示你应该在时间轴上将纯音乐轨拖动多少。

### 手动偏移

如果自动对齐的结果稍有偏差（例如由于源音频噪声极大），可以使用"自动对齐"标签页中的**手动偏移 (ms)** 滑块进行微调。显示窗口中的最终偏移量 = 算法偏移量 + 手动偏移量。

---

## 配置

设置保存在 `config.json` 中，可在设置标签页中调整：

| 设置项 | 默认值 | 说明 |
|---|---|---|
| 语言 | 简体中文 | 界面语言（English / 中文）；需重启生效 |
| 视频流直拷 | 开 | 跳过视频重编码；近乎瞬时导出，零画质损失 |
| GPU 加速渲染 | 关 | 转码时使用 NVIDIA NVENC（仅在关闭"流直拷"时生效） |
| 视频码率 | 10000k | 编码码率：6000k（适合分享）、10000k（推荐）、20000k（存档级） |
| 完成后打开文件夹 | 开 | 导出完成后自动打开目标文件夹 |

---

## 项目结构

```
RhythmAlign/
├── ui_main.py              # PyQt6 + QFluentWidgets 图形界面（对齐、分析、关于、设置）
├── auto_sync.py            # 核心对齐引擎 & ffmpeg 导出管线
├── diagnose_offset.py      # 命令行诊断工具，用于排查对齐失败
├── locales/
│   ├── zh_CN.json          # 简体中文翻译
│   └── en_US.json          # 英文翻译
├── requirements.txt        # Python 依赖列表
├── logo.png                # 应用图标（对立鸭）
├── logo.ico                # Windows .ico 版本
├── github.png              # GitHub 品牌标识
├── bilibili.png            # Bilibili 品牌标识
└── config.json             # 用户设置（自动生成）
```

---

## 参与贡献

欢迎贡献！如有重大改动，请先开 Issue 讨论你的设想。

以下方向尤其需要帮助：
- **macOS / Linux 兼容性** — 核心引擎是跨平台的；非 Windows 平台的 GUI 测试
- **额外的对齐策略** — 如 MFCC、DTW 或深度学习方法作为第三级回退
- **多语言界面** — 添加新的语言翻译文件

---

## 版权与免责声明

### 代码许可

本项目采用 **MIT License** 开源。详见 [LICENSE](LICENSE)。

### 素材致谢

应用图标及品牌素材裁剪自 **"对立鸭"** 表情包系列，由以下作者在约稿方的授权下慷慨提供免费开源使用许可：

> **春也Haruya**（B站 UID: [3280](https://space.bilibili.com/3280)）
>
> 特别感谢约稿方授予开源使用授权。

**角色与 IP 声明：** 对立（Tairitsu）及相关角色素材、名称与知识产权归 **lowiro** 所有。RhythmAlign 为独立、非商业的开源社区工具，与 lowiro 无任何关联、背书或合作关系。

### ⚠️ 合理使用声明

- 本软件**完全免费开源**。若您是付费获取，请立即申请退款。
- 仅供**个人非商业用途**。禁止用于盈利或与商业产品捆绑分发。

---

<p align="center">
  <sub>献给音游社区，用 ♪ 打造。</sub>
</p>
