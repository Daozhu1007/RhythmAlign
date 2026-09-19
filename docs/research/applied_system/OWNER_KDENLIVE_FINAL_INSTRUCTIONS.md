# 你现在要做什么

你只需要用 Kdenlive 完成 10 个小任务。每个任务约 3–5 分钟。

**重要:做完 10 个任务之前,不要运行、查看或询问任何自动对齐(自动同步)的结果。所有自动系统的最终结果都处于封存状态,必须等你做完这 10 个任务。**

---

## 准备(只做一次)

- Kdenlive 已经装好了(版本 26.08.1)。
- 打开一个命令行窗口(Win+R,输入 `cmd`,回车),然后输入:

```
cd /d D:\Code\RhythmAlign\experiments\applied_system\final_pack\kdenlive
```

- 计时用这个命令(把 pair01 换成当前任务名):

```
python owner_timer.py pair01
```

- 第一次打开 Kdenlive 如果出现设置向导,直接点「关闭」或「确定/跳过」即可。

---

## 每个任务的步骤(pair01 一直做到 pair10)

按顺序做 pair01、pair02……一直到 pair10。每个 pair 做同样的操作:

1. 在命令行输入 `python owner_timer.py pair01` (按回车)。计时开始后不要再休息。
2. 打开文件夹 `owner_pack\pair01`,里面有两条音频:
   - `recording.wav` —— 现场录音
   - `reference.wav` —— 干净的参考音乐
3. 打开 Kdenlive,新建一个空白工程。
4. 把这两条音频从文件夹拖进 Kdenlive 上方的「项目剪辑箱(Project Bin)」。
5. 这两条都是纯音频文件,必须放在**音频轨道**上:把 `recording.wav` 拖到 **A1** 音频轨道,把 `reference.wav` 拖到 **A2** 音频轨道,**两条都从最左边 00:00 位置开始放**。
   - 新建空白工程默认就有 A1、A2 两条音频轨道。如果只有一条音频轨道,在时间轴左侧任意轨道头上**右键 → 「插入轨道」**,轨道类型选**「音频」**,加出第二条后再放。
6. 在时间轴上**右键点击 `recording.wav` 那一段**,选:
   - **「设置音频辅助线」(Set Audio Reference)**
7. 再**左键单击选中 `reference.wav` 那一段**,右键,选:
   - **「对齐音频到辅助线」(Align Audio to Reference)**
8. 等待 Kdenlive 自己完成对齐。它会自动移动 `reference.wav` 的位置。
   - **不要手动拖动波形去对齐,不要剪断、移动或修改 `recording.wav`。**
   - 如果 Kdenlive 弹出「无法对齐 / 未找到匹配」或错误窗口,**不要手动补救**,记住发生了什么就行。
9. 保存工程:**文件 → 另存为**,存到 `pair01` 文件夹里,文件名叫 **`pair01.kdenlive`**。
10. 回到命令行,按回车结束计时,然后按提示输入 Kdenlive 的表现:
    - `1` = 对齐正常完成
    - `2` = Kdenlive 说无法对齐 / 未找到匹配
    - `3` = 弹出了错误窗口
    - `4` = 其他情况(写一句备注)
11. 继续下一个 pair(`python owner_timer.py pair02`……一直到 pair10)。

随时可以查看进度:

```
python owner_timer.py --status
```

---

## 中途可以休息吗

可以。**每按一次回车之间就是一对的用时**,pair 之间的休息不计入。但一旦输入了 `python owner_timer.py pairNN`,就要一口气做完这一个 pair 再休息。

## 遇到问题

- Kdenlive 弹任何窗口、报任何错:照原样记录(选项 2/3/4),不要想办法绕过。
- 计时器说某个 pair 已经计时过:跳过它,做下一个。
- 其他任何疑问:直接停下来,全部做完后一起说。
