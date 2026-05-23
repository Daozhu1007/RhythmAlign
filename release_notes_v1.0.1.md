# RhythmAlign v1.0.1 Release Notes

## 🚀 核心优化与重构

- **音频解析正则放宽**：`_parse_duration_hms` 现已兼容非标准 FFmpeg 容器返回的整数秒格式，避免因 duration 解析失败导致的对齐流程中断。
- **FFmpeg 滤镜图精简**：当音视频偏移量可忽略（<1ms）时，自动跳过 `adelay`/`atrim` 滤镜插入，减少不必要的滤镜图复杂度与 CPU 开销。
- **Worker 线程模板方法重构**：抽取 `BaseMediaWorker(QThread)` 基类，统一管理信号发射与错误处理逻辑，消除 Sync/ Analyze 双 Worker 中的重复样板代码（DRY）。
- **Chroma 交叉相关调用统一**：`diagnose_offset.py` 中手写的 chroma 互相关逻辑已替换为对 `_align_chroma` 的标准调用，确保诊断工具与主对齐引擎行为一致。
- **I18n 降级容错机制**：`I18nManager.tr()` 在格式化字符串异常时不再静默吞错，改为输出至 stderr 并返回安全降级文本，防止翻译文件损坏导致诊断信息丢失。
- **移动端视频兼容性加固**：针对 iPhone 录制的 MOV/HEVC/VFR 视频，增加 `+genpts` / `-avoid_negative_ts make_zero` 时间戳修复、Dolby Vision DOVI 元数据剥离、以及无声音轨的 probe 保护。
- **配置清理**：移除废弃的 `config/config.json`（已统一由项目根目录 `config.json` 接管）。

## 🐛 问题修复

- 修复低质量麦克风录音（如手持设备）在 Chroma CENS 对齐策略下 Z-score 低于噪声阈值时，`argmax` 错误落在 lag=0 导致返回虚假偏移量 0.0000s 的问题。现已自动降级至 Onset Envelope 节奏检测策略作为兜底。
- 修复 `QLineEdit.text()` 与 `placeholderText` 的逻辑误判——原代码通过占位文本字符串比对验证路径有效性，实际 `text()` 永不返回 `placeholderText`，改为 `os.path.isfile()` 硬检查。
- 修复 `OptionsSettingCard` 中使用不存在的 `comboBox` 信号，替换为正确的 `optionChanged` 信号。
- 修复并发执行时 `int(time.time())` 临时文件名碰撞风险，改用 `uuid.uuid4().hex`。
- 修复 `librosa.load()` 未指定 `mono=True` 导致双声道重复切片，浪费约 50% 特征提取内存。
- 修复 `errors='ignore'` 导致的静默 Unicode 损坏，统一替换为 `errors='replace'`。

## 📝 开发者备注

- **已知问题（暂缓处理）**：处理超长音频（>1 小时）时存在 OOM（内存溢出）风险，此问题已在知悉列表中，将在后续版本中通过流式特征提取或分段对齐策略解决。
- 新增 `diagnose_offset.py` 独立诊断脚本，可按策略输出相关性质量剖面，便于排查对齐失败案例。
- License 已由 CC BY-NC 4.0 切换为 PolyForm Noncommercial 1.0.0，提供更强代码保护。Windows 安装包现已绑定 LICENSE 文件。
