"""
诊断脚本：分析为什么 find_offset 对特定文件对返回 ~0 的结果。
用法：python diagnose_offset.py "视频文件路径" "音频文件路径"
"""
import sys
import os
import shutil
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auto_sync import (
    extract_audio, _parse_duration_hms, _align_chroma, _correlation_z_score,
    _independent_peak_ratio, _subprocess_no_window_kwargs,
)
import imageio_ffmpeg
import librosa
import subprocess
import tempfile
import uuid

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 22050
HOP_LENGTH = 512


def check_audio_silence(y, label):
    """检查音频信号是否接近静音。"""
    rms = np.sqrt(np.mean(y ** 2))
    peak = np.max(np.abs(y))
    duration = len(y) / SR
    print(f"  [{label}] 时长={duration:.2f}s, RMS={rms:.6f}, Peak={peak:.6f}")
    if rms < 1e-6:
        print(f"  >>> 警告: {label} 几乎是静音! (RMS ≈ 0)")
    if duration < 1.0:
        print(f"  >>> 警告: {label} 时长极短 (<1s)，可能解码失败!")
    return rms, peak, duration


def check_chroma_variance(feat, label):
    """检查 Chroma 特征是否有意义的差异。"""
    feat_std = np.std(feat, axis=1)
    feat_mean = np.mean(feat, axis=1)
    total_var = np.var(feat)
    print(f"  [{label}] Chroma shape={feat.shape}, 总方差={total_var:.6f}")
    if total_var < 1e-8:
        print(f"  >>> 警告: {label} 的 Chroma 特征几乎无变化! 互相关将退化为噪声!")
    return total_var


def compute_correlation_quality(correlation, offset_seconds, z_score):
    """评估互相关结果的可靠性。"""
    peak_val = np.max(correlation)
    mean_val = np.mean(correlation)
    std_val = np.std(correlation)
    min_peak_separation = max(1, int((1.5 * SR) / HOP_LENGTH))
    peak_ratio = _independent_peak_ratio(correlation, min_peak_separation)

    print(f"\n  互相关质量评估:")
    print(f"    峰值={peak_val:.2f}, 均值={mean_val:.2f}, 标准差={std_val:.2f}")
    print(f"    独立峰值比={peak_ratio:.2f} (越高越可靠, <1.05 说明候选峰几乎并列)")
    print(f"    峰值 Z-score={z_score:.2f} (>5 通常可靠, <3 可能为噪声)")
    print(f"    计算偏移量={offset_seconds:+.4f}s")

    if z_score < 3:
        print(f"  >>> 警告: Z-score 很低，相关峰值可能是随机噪声！算法对这个文件对不可靠。")
    if peak_ratio < 1.05:
        print("  >>> 警告: 最佳峰值与其他候选几乎并列，建议人工复核。")


def _find_ffprobe_bin():
    bundled_candidate = os.path.join(
        os.path.dirname(FFMPEG),
        "ffprobe.exe" if os.name == "nt" else "ffprobe",
    )
    if os.path.exists(bundled_candidate):
        return bundled_candidate
    return shutil.which("ffprobe")


def check_video_audio_source(video_path):
    """检查视频音频轨的来源信息。"""
    ffprobe_bin = _find_ffprobe_bin()
    if ffprobe_bin is None:
        print("\n  ffprobe 未找到，跳过视频音频轨元数据探测。")
        return

    try:
        result = subprocess.run(
            [ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_format",
             "-show_streams", video_path],
            **_subprocess_no_window_kwargs(
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, errors='ignore', timeout=30,
            )
        )
        import json
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "audio":
                codec = stream.get("codec_name", "?")
                channels = stream.get("channels", "?")
                sample_rate = stream.get("sample_rate", "?")
                bit_rate = stream.get("bit_rate", "?")
                duration = stream.get("duration", "?")
                tags = stream.get("tags", {})
                handler = tags.get("handler_name", "?")
                print(f"\n  视频音频轨信息:")
                print(f"    编码: {codec}, {channels}ch, {sample_rate}Hz, 比特率={bit_rate}")
                print(f"    时长: {duration}s, 处理器: {handler}")
                if "Soundflower" in handler or "Loopback" in handler or "BlackHole" in handler:
                    print(f"  >>> 检测到虚拟音频设备! 视频可能包含内录音频。")
                break
    except Exception as e:
        print(f"  ffprobe 探测失败: {e}")


def diagnose(video_path, music_path):
    print("=" * 60)
    print("RhythmAlign find_offset 诊断工具")
    print("=" * 60)

    print(f"\n[1] 检查输入文件")
    print(f"  视频: {video_path}  (存在={os.path.exists(video_path)})")
    print(f"  音乐: {music_path}  (存在={os.path.exists(music_path)})")

    check_video_audio_source(video_path)

    print(f"\n[2] 提取并分析原始音频")
    temp_dir = tempfile.gettempdir()
    temp_v = os.path.join(temp_dir, f"ra_diag_video_{uuid.uuid4().hex}.wav")
    temp_m = os.path.join(temp_dir, f"ra_diag_music_{uuid.uuid4().hex}.wav")

    try:
        extract_audio(FFMPEG, video_path, temp_v, SR)
        extract_audio(FFMPEG, music_path, temp_m, SR)

        # 也检查 WAV 文件大小
        v_size = os.path.getsize(temp_v)
        m_size = os.path.getsize(temp_m)
        print(f"  视频解码 WAV 大小: {v_size / 1024:.1f} KB, 音乐解码 WAV 大小: {m_size / 1024:.1f} KB")

        y_video, sr_v = librosa.load(temp_v, sr=None, mono=True)
        y_music, sr_m = librosa.load(temp_m, sr=None, mono=True)

        print(f"\n[3] 音频内容分析")
        check_audio_silence(y_video, "视频音频")
        check_audio_silence(y_music, "纯净音乐")

        print(f"\n[4] Chroma CENS 特征分析")
        feat_video = librosa.feature.chroma_cens(y=y_video, sr=SR, hop_length=HOP_LENGTH)
        feat_music = librosa.feature.chroma_cens(y=y_music, sr=SR, hop_length=HOP_LENGTH)

        v_var = check_chroma_variance(feat_video, "视频 Chroma")
        m_var = check_chroma_variance(feat_music, "音乐 Chroma")

        print(f"\n[5] 互相关分析")
        result, z_score, correlation = _align_chroma(y_video, y_music, SR, HOP_LENGTH)

        compute_correlation_quality(correlation, result, z_score)

        print(f"\n[6] 诊断结论")
        print("-" * 40)

        if result == 0.0 and v_var > 1e-8 and m_var > 1e-8:
            # 特征都有意义但偏移为 0
            min_peak_separation = max(1, int((1.5 * SR) / HOP_LENGTH))
            peak_ratio = _independent_peak_ratio(correlation, min_peak_separation)

            if peak_ratio < 1.05:
                print("结论: 互相关没有找到明显峰值，Chroma 特征匹配失败。")
                print("原因: 视频中的音频和纯净音乐的音色差异太大（如外录噪音、")
                print("      压缩失真），导致 Chroma CENS 特征无法正确匹配。")
                print("建议: 尝试以下方法之一：")
                print("  1. 使用手动偏移滑块手动标定偏移量")
                print("  2. 如果视频包含内录音轨，检查是否可以提取无噪音的内录音频")
                print("  3. 对视频音频做降噪预处理后重试")
            else:
                print("结论: 两个音频信号确实在时间轴上对齐（offset ≈ 0）。")
                print("可能原因: 视频包含内录的游戏音频（如系统录屏/虚拟声卡录制），")
                print("         视频中的背景音乐已经和纯净 MP3 天然对齐。")
                print("注意: 如果这是手元视频（拍手的），音频对齐 ≠ 画面同步。")
                print("      手部动作相对于游戏音频固定有延迟，0 偏移反而是正确的。")
        elif v_var < 1e-8:
            print("结论: 视频音频轨的 Chroma 特征方差接近 0。")
            print("原因: 视频可能没有有效的音频轨，或音频被错误解码。")
            print("建议: 检查视频文件是否包含正确的音频流。")
        elif m_var < 1e-8:
            print("结论: 音乐文件的 Chroma 特征方差接近 0。")
            print("原因: 音乐文件可能损坏或为静音。")
        else:
            print(f"结论: 算法正常工作，偏移量 = {result:+.4f}s")

    finally:
        for f in [temp_v, temp_m]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python diagnose_offset.py <视频路径> <音频路径>")
        sys.exit(1)
    diagnose(sys.argv[1], sys.argv[2])
