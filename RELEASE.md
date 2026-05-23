# RhythmAlign Release 发布流程

> 每次需要发布新版本时，将本文档交给 Claude Code，由它按以下步骤全自动完成。

---

## 前置准备

- 确认当前在 `main` 分支，工作区干净。
- 确认已安装：Python 3.10+、PyInstaller、Inno Setup 6（路径 `D:\Program Files\Inno Setup 6\ISCC.exe`）、GitHub CLI（`gh`）并已登录。
- 确认 `RhythmAlign.spec`、`RhythmAlign.iss`、`ui_main.py` 三个文件存在且内容正确。

---

## 第一步：环境清理与版本号更新

1. 清理冗余目录和文件：
   - 删除所有 `__pycache__/` 目录。
   - 删除 `build/` 目录。
   - 删除旧 `dist/` 目录。
   - 检查并确保 `config/config.json`（废弃）已不存在，仅保留根目录 `config.json`。

2. 版本号更新（以目标版本号 `X.Y.Z` 为例）：
   - 检查 `ui_main.py` 中是否有 `VERSION` / `__version__` 常量，如有则更新。
   - 检查 `RhythmAlign.spec` 中是否有版本号引用，如有则更新。
   - 更新 `RhythmAlign.iss` 中两处：
     - `#define MyAppVersion "X.Y.Z"`（第 2 行）
     - `OutputBaseFilename=RhythmAlign_vX.Y.Z_Setup`（第 19 行）

---

## 第二步：PyInstaller 编译打包

```bash
pyinstaller RhythmAlign.spec --clean --noconfirm
```

执行完毕后验证 `dist/RhythmAlign/RhythmAlign.exe` 是否生成。若失败则停止并排查。

---

## 第三步：Inno Setup 制作安装包

1. 编译命令：
   ```bash
   "D:\Program Files\Inno Setup 6\ISCC.exe" RhythmAlign.iss
   ```

2. 验证安装包已生成：`dist/RhythmAlign_vX.Y.Z_Setup.exe`。

---

## 第四步：制作便携版 ZIP

```bash
powershell -Command "Compress-Archive -Path 'dist\RhythmAlign\*' -DestinationPath 'dist\RhythmAlign-vX.Y.Z-Portable.zip' -Force"
```

---

## 第五步：撰写 Release Notes

文件命名：`release_notes_vX.Y.Z.md`

### 必须包含的章节（顺序固定）

1. **Quote 引导语**：
   ```markdown
   > 音游手元音频自动对齐工具 | Auto Audio-Video Sync for Rhythm Game Hand-Cams
   ```

2. **核心特性 | Core Features** — 保持与上一版本一致，仅在有重大功能变化时更新。

3. **vX.Y.Z 更新内容 | What's New**（小版本）/ **vX.Y.Z 重大更新 | Major Changes**（大版本）：
   - `🚀 优化与重构` 和 `🐛 问题修复` 两个子章节。
   - 内容从 `git log` 提取，用中文撰写，每条一句，技术细节精确。

4. **下载 | Downloads** — 使用表格：
   ```markdown
   | 类型 | 文件名 |
   |---|---|
   | 安装版 (推荐) | `RhythmAlign_vX.Y.Z_Setup.exe` |
   | 便携版 | `RhythmAlign-vX.Y.Z-Portable.zip` |
   ```

5. **安装说明 | Installation**：
   ```markdown
   **Windows 10/11 x64**:
   - **Setup 版**: 双击安装程序，按向导完成安装。自动创建桌面与开始菜单快捷方式。
   - **Portable 版**: 解压 ZIP 到任意目录，直接运行 `RhythmAlign.exe`。

   首次启动时如需 Microsoft Visual C++ Redistributable，请从 [微软官方](https://aka.ms/vs/17/release/vc_redist.x64.exe) 下载安装。
   ```

6. **已知限制 | Known Issues**：
   - 仅支持 Windows x64 平台。
   - GPU 加速仅支持 NVIDIA 显卡 (NVENC)。
   - 当视频内录音频与纯净音乐差异过大时，自动对齐可能失败，请使用手动微调。
   - 超长音频 (>1 小时) 存在 OOM 风险（如已修复则删除此条）。

7. **许可 | License**：
   ```markdown
   本软件基于 PolyForm Noncommercial 1.0.0 许可协议，仅供个人非商业使用。详见 [LICENSE](https://github.com/Daozhu1007/RhythmAlign/blob/main/LICENSE)。
   ```

8. **结尾署名**：
   ```markdown
   *Limitime — <Month> <Year>*
   ```

### Release Notes 风格规范

- **不要在正文中写 `# 一级标题`**，因为 GitHub Release 标题本身已显示版本号，重复会冗余。
- 正文以 `>` 引用块开头（一句话定位描述）。
- 所有章节标题使用 `## 二级标题`。
- 章节间用 `---` 水平线分隔。
- 中英文并存的标题用 `|` 分隔（如 `## 核心特性 | Core Features`）。
- 内容以中文为主，技术名词保留英文原名（如 `adelay`/`atrim`、`BaseMediaWorker`）。
- 文件名使用反引号包裹。

### 参考链接

- 最新 Release 风格参考：https://github.com/Daozhu1007/RhythmAlign/releases/latest

---

## 第六步：推送到 GitHub 并创建 Release

1. 提交所有变更：
   ```bash
   git add RhythmAlign.iss release_notes_vX.Y.Z.md
   git commit -m "chore: bump version to vX.Y.Z and prepare release"
   ```

2. 打标签：
   ```bash
   git tag vX.Y.Z
   ```

3. 推送分支与标签：
   ```bash
   git push origin main && git push --tags
   ```

4. 创建 GitHub Release 并上传资产：
   ```bash
   gh release create vX.Y.Z \
     ./dist/RhythmAlign_vX.Y.Z_Setup.exe \
     ./dist/RhythmAlign-vX.Y.Z-Portable.zip \
     -F release_notes_vX.Y.Z.md \
     -t "RhythmAlign vX.Y.Z"
   ```

   如果 Release 已存在需要补充资产：
   ```bash
   gh release upload vX.Y.Z ./dist/RhythmAlign-vX.Y.Z-Portable.zip --clobber
   ```

5. 验证 Release 页面，确认两个资产均已上传且 Release Notes 格式正确。

---

## 发行物命名规范

| 类型 | 格式 | 示例 |
|---|---|---|
| 安装包 | `RhythmAlign_vX.Y.Z_Setup.exe` | `RhythmAlign_v1.0.1_Setup.exe` |
| 便携版 | `RhythmAlign-vX.Y.Z-Portable.zip` | `RhythmAlign-v1.0.1-Portable.zip` |
> **注意**：安装包用下划线 `_` 分隔版本号，便携版用短横线 `-`。这是历史约定，不要统一。

---

## 善后

- **不要将 `release_notes_vX.Y.Z.md` 提交到仓库**。GitHub Release 的 body 存储在 GitHub 服务器端，与仓库代码无关。本地 `.md` 文件只是 `gh release create -F` 的临时载体，发布完成后直接删除即可。
- 同理，**不要将 Release Notes 文件 push 到云端**。即使 push 了，删除后 `git push` 也不会影响已发布的 Release 页面内容。
- 发布完成后删除本地 `release_notes_vX.Y.Z.md`：`rm release_notes_vX.Y.Z.md`
- 不要提交 `dist/` 目录和 `build/` 目录（由 `.gitignore` 排除）。
