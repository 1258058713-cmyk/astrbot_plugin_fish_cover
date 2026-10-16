# utils/audio.py
import os
import subprocess
from astrbot.api import logger


def mix_audio(vocals_path: str, accompaniment_path: str, output_path: str) -> str:
    """
    用 FFmpeg 把翻唱后的人声和伴奏混在一起。
    :param vocals_path: 翻唱后的人声文件路径
    :param accompaniment_path: 伴奏文件路径
    :param output_path: 混音后的输出路径
    :return: 混音后的文件路径
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", vocals_path,
        "-i", accompaniment_path,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest",
        output_path,
    ]
    logger.info(f"正在混音: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def convert_format(input_path: str, output_path: str, fmt: str = "wav") -> str:
    """
    用 FFmpeg 转换音频格式，比如 MP3 转 WAV。
    :param input_path: 输入文件路径
    :param output_path: 输出文件路径
    :param fmt: 目标格式，如 wav、mp3
    :return: 转换后的文件路径
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-f", fmt,
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def get_duration(audio_path: str) -> float:
    """
    用 ffprobe 获取音频时长（秒）。
    :return: 音频时长，失败时返回 0.0
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"获取音频时长失败: {e}")
        return 0.0


def clean_temp_files(*paths: str):
    """
    清理临时文件，不存在的路径会自动跳过。
    """
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f"已清理临时文件: {path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {path}, {e}")