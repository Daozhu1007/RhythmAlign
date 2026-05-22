# RhythmAlign v1.0.0 Preview

> 音游手元音频自动对齐工具 | Auto Audio-Video Sync for Rhythm Game Hand-Cams

---

## 核心特性 | Core Features

- **Chroma + Onset 两级级联算法** — 先通过 Chroma 特征粗定位，再以 Onset 包络精细互相关，兼顾大偏移搜索与子样本级精度。
- **彻底脱离 MoviePy** — 全面迁移至 `imageio-ffmpeg` + FFmpeg 子进程底层重构，流拷贝与重编码双路径，支持 GPU 硬件加速 (NVIDIA NVENC)。
- **无损流拷贝模式** — 默认开启 Stream Copy，直接重封装音轨，100% 保留原始画质并极速导出。
- **纯分析模式** — 仅计算音乐相对视频的同步偏移量，输出精确拖拽指南，无需渲染等待。
- **中英双语界面** — 基于 JSON 的轻量 i18n 引擎，运行时切换语言 (需重启生效)。
- **PyQt6 + QFluentWidgets** — 现代深色主题 UI，流畅亚克力导航，高 DPI 适配。

---

## 技术架构 | Tech Stack

| 模块 | 技术 |
|---|---|
| UI 框架 | PyQt6 + QFluentWidgets |
| 音频分析 | librosa (Chroma + Onset + F0 Contour) |
| 互相关计算 | scipy.signal.correlate |
| 视频处理 | imageio-ffmpeg + FFmpeg CLI |
| 打包分发 | PyInstaller + Inno Setup |
| 国际化 | 自研 JSON i18n 引擎 |

---

## 下载 | Downloads

| 类型 | 文件名 |
|---|---|
| 安装版 (推荐) | `RhythmAlign-v1.0.0-Preview-Setup.exe` |
| 便携版 | `RhythmAlign-v1.0.0-Preview-Portable.zip` |

---

## 安装说明 | Installation

**Windows 10/11 x64**:
- **Setup 版**: 双击安装程序，按向导完成安装。自动创建桌面与开始菜单快捷方式。
- **Portable 版**: 解压 ZIP 到任意目录，直接运行 `RhythmAlign.exe`。

首次启动时如需 Microsoft Visual C++ Redistributable，请从 [微软官方](https://aka.ms/vs/17/release/vc_redist.x64.exe) 下载安装。

---

## 已知限制 | Known Issues

- 仅支持 Windows x64 平台。
- GPU 加速仅支持 NVIDIA 显卡 (NVENC)。
- 当视频内录音频与纯净音乐差异过大时，自动对齐可能失败，请使用手动微调。

---

## 许可 | License

本软件为免费开源社区工具，仅供个人学习使用。详见 [LICENSE](https://github.com/Daozhu1007/RhythmAlign)。

---

*Limitime — May 2026*
