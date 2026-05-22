<p align="center">
  <a href="README.md">English</a> &nbsp;|&nbsp; <a href="README_zh.md"><b>简体中文</b></a>
</p>

<p align="center">
  <img src="logo.png" width="128" alt="Logo">
</p>

<h1 align="center">RhythmAlign</h1>

<p align="center">
  音游手元自动化音频对齐工具，让制作高质量手元更轻松。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

<p align="center">
  <img src="assets/screenshot_zh.png" width="720" alt="软件界面">
</p>

---

## 为什么使用 RhythmAlign？

在传统剪辑软件（PR、剪映等）中对手元录像和纯净音频做对齐，是个体力活：凭肉眼反复拖动波形、渲染导出、拉回时间轴检查。当机载麦克风录到的是刺耳的键盘敲击和房间混响时——这在街机手元中几乎是常态——剪辑软件里的波形图基本没法看。

RhythmAlign 把这个过程自动化：

1. 从视频和参考音乐中分别提取音频。
2. 使用双策略算法找到最佳对齐偏移量（优先使用 Chroma 旋律匹配；当录音噪声过大时自动回退到 Onset 节拍匹配）。
3. 输出新的 MP4 文件——视频流原封不动，音轨替换为已同步的纯音频。

---

## 核心特性

### 音频对齐

| 策略 | 原理 | 适用场景 |
|---|---|---|
| Chroma | 匹配两条音轨的和声特征（音高分布） | 干净的录音：桌面内录、线路输入 |
| Onset（回退） | 匹配音符起始的瞬态节拍 | 嘈杂的录音：手机外录、街机环境声 |

算法优先尝试 Chroma。若结果未通过统计置信度检验，自动切换至 Onset 重试。两步均失败 → UI 直接报错，绝不悄悄导出对齐歪了的结果。

### 视频导出

- **流拷贝（默认）：** 原始视频比特流 1:1 复刻。不重编码、不损失画质。三分钟的视频几秒内完成。
- **重编码（可选）：** NVIDIA NVENC 加速，6000k / 10000k / 20000k 三档码率。适合需要对编码格式或体积做精确控制的场景。

### 手机视频兼容性

手机录制的视频——尤其是 iPhone 的 MOV 文件——经常让 ffmpeg 出问题：

| 问题 | 修复方式 |
|---|---|
| 可变帧率（VFR）导致音画漂移 | `-fflags +genpts` 强制重建统一时间戳 |
| 负时间戳导致播放器同步异常 | `-avoid_negative_ts make_zero` |
| QuickTime 编辑表元数据导致封装崩溃 | `-map_metadata -1` 剥离所有私有元数据 atom |
| moov atom 在文件末尾导致无法流式播放 | `-movflags +faststart` |

### 其他

- **纯分析模式：** 只算偏移量不导出。把数值填进任何剪辑软件的时间轴即可。
- **手动偏移微调：** ±500 ms 滑块，应对源音频严重降质的情况。
- **内置诊断工具：** `diagnose_offset.py` 输出 Chroma 特征方差、相关度 Z-score 及音轨元数据，方便排查。
- **中英双语界面：** 简体中文 / English，设置页随时切换。

---

## 快速开始

### 环境

- Windows 10 / 11
- Python 3.9+（64 位）
- FFmpeg 由 `imageio-ffmpeg` 自动捆绑，无需单独安装

### 安装

```bash
git clone https://github.com/Daozhu1007/RhythmAlign.git
cd RhythmAlign
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 启动

```bash
python ui_main.py
```

### 调试顽固文件对

```bash
python diagnose_offset.py "path/to/video.mp4" "path/to/music.mp3"
```

---

## 版权与免责声明

### 应用图标

应用图标裁剪自 **"对立鸭"** 表情包系列，由以下画师创作：

> **春也Haruya**（[B站 UID: 3280](https://space.bilibili.com/3280)）

经约稿方授予免费开放使用授权。在此对画师与约稿方致以诚挚感谢。

### IP 声明

**对立（Tairitsu）** 及相关角色设计、名称、知识产权归 **lowiro** 所有。RhythmAlign 为独立的非商业开源社区同人工具，与 lowiro 无关，亦未获其背书。

### 合理使用

- 本软件**完全免费开源**（MIT）。若您付费获取，请立即申请退款。
- **仅供个人、非商业用途。** 禁止以盈利为目的二次分发。

---

## 许可协议

MIT。详见 [LICENSE](LICENSE)。

---

<p align="center">
  <a href="https://github.com/Daozhu1007/RhythmAlign"><img src="github.png" height="22"></a>
  &nbsp;
  <a href="https://space.bilibili.com/477852567"><img src="bilibili.png" height="22"></a>
</p>
