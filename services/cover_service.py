# services/cover_service.py
import os
import tempfile
import requests
from astrbot.api import logger
from qqmusic_api import Client

from .fish_audio import FishAudioService
from .demucs_worker import MDXSeparator
from ..utils.audio import mix_audio


class CoverService:
    def __init__(self, fish_api_key: str, model_path: str, temp_dir: str = None):
        """
        初始化翻唱服务
        :param fish_api_key: Fish Audio 的 API Key
        :param model_path: MDX 模型文件的完整路径
        :param temp_dir: 临时文件目录，不传则用系统默认
        """
        self.fish = FishAudioService(api_key=fish_api_key)
        self.qq_client = Client(credential=self.credential) if hasattr(self, 'credential') else Client()

        # 只加载一次模型，后续一直复用
        logger.info(f"正在加载 MDX 模型: {model_path}")
        self.separator = MDXSeparator(model_path)

        self.temp_dir = temp_dir or tempfile.gettempdir()

    def _download_song(self, song_name: str) -> str:
    """
    搜歌并下载，从搜索结果前 5 条中依次尝试，直到成功为止。
    :param song_name: 歌曲名
    :return: 下载到本地的文件路径
    """
    logger.info(f"正在搜索歌曲: {song_name}")
    result = self.qq_client.search(song_name)

    if not result or not result.get("data"):
        raise RuntimeError(f"找不到歌曲《{song_name}》")

    # 只取前 5 条尝试，避免卡太久
    candidates = result["data"][:5]

    for index, song in enumerate(candidates, start=1):
        song_mid = song.get("mid")
        song_title = song.get("title", "未知歌曲")
        singers = song.get("singer", [])
        singer_name = "、".join([s.get("name", "") for s in singers]) if singers else "未知歌手"

        # 跳过没有 mid 的结果
        if not song_mid:
            continue

        try:
            # 尝试获取播放链接
            audio_url = self.qq_client.get_song_url(song_mid)
            if not audio_url:
                logger.warning(f"[{index}/5] 《{song_title}》- {singer_name} 无可用链接，尝试下一个")
                continue

            # 下载
            save_path = os.path.join(self.temp_dir, f"{song_title}.mp3")
            resp = requests.get(audio_url, timeout=60)
            if resp.status_code != 200 or len(resp.content) < 1024:
                logger.warning(f"[{index}/5] 《{song_title}》- {singer_name} 下载失败，尝试下一个")
                continue

            with open(save_path, "wb") as f:
                f.write(resp.content)

            logger.info(f"[{index}/5] 成功下载: {song_title} - {singer_name} -> {save_path}")
            return save_path

        except Exception as e:
            logger.warning(f"[{index}/5] 处理《{song_title}》时出错: {e}，尝试下一个")
            continue

    raise RuntimeError(f"《{song_name}》的前 5 条搜索结果都无法下载")
   
    async def generate_cover(self, song_name: str) -> str:
        """
        完整的翻唱流程：下载 → 分离 → 翻唱 → 混音
        :param song_name: 歌曲名
        :return: 最终翻唱文件路径
        """
        # 1. 下载原曲
        logger.info(f"开始处理歌曲: {song_name}")
        async with self.qq_client as client:
            original_path = self._download_song(song_name)

        # 2. 分离人声和伴奏（调用已加载好的模型实例，不再重新加载）
        output_dir = os.path.join(self.temp_dir, "separated")
        vocals_path, accompaniment_path = self.separator.separate(
            original_path, output_dir
        )

        # 3. 用 Fish Audio 翻唱人声
        logger.info("正在用 Fish Audio 翻唱人声...")
        converted_vocals = self.fish.voice_conversion(vocals_path)

        # 4. 混音
        logger.info("正在混音...")
        output_path = os.path.join(self.temp_dir, "final_cover.mp3")
        final_path = mix_audio(converted_vocals, accompaniment_path, output_path)

        logger.info(f"翻唱完成: {final_path}")
        return final_path