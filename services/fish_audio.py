# services/fish_audio.py
import os
import requests
from astrbot.api import logger


class FishAudioService:
    def __init__(self, api_key: str, reference_id: str = ""):
        """
        初始化 Fish Audio 服务
        :param api_key: Fish Audio 的 API Key
        :param reference_id: 目标音色 ID（用于 voice conversion）
        """
        self.api_key = api_key
        self.reference_id = reference_id
        self.base_url = "https://api.fish.audio"

    def _headers(self) -> dict:
        """构造请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def voice_conversion(self, audio_path: str, reference_id: str = None) -> str:
        """
        音色转换：把输入的人声替换成目标音色
        :param audio_path: 输入人声文件路径
        :param reference_id: 目标音色 ID，不传则用初始化时设置的
        :return: 转换后的音频文件路径
        """
        if not self.api_key:
            raise ValueError("Fish Audio API Key 未配置")

        ref_id = reference_id or self.reference_id
        if not ref_id:
            raise ValueError("Fish Audio 参考音色 ID 未配置")

        # 读取人声文件并上传，获取上传后的文件 ID
        logger.info(f"正在上传人声文件到 Fish Audio: {audio_path}")
        upload_url = f"{self.base_url}/v1/file"
        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            upload_resp = requests.post(upload_url, headers=headers, files=files, timeout=120)

        if upload_resp.status_code != 200:
            raise RuntimeError(f"上传文件失败: {upload_resp.status_code} {upload_resp.text}")

        file_id = upload_resp.json().get("id")
        if not file_id:
            raise RuntimeError(f"上传文件返回异常: {upload_resp.text}")

        # 调用 voice conversion 接口
        logger.info(f"正在使用音色 {ref_id} 进行音色转换...")
        convert_url = f"{self.base_url}/v1/voice/conversion"
        payload = {
            "audio": file_id,
            "reference_id": ref_id,
            "format": "wav",
        }
        convert_resp = requests.post(
            convert_url,
            headers=self._headers(),
            json=payload,
            timeout=300,
        )

        if convert_resp.status_code != 200:
            raise RuntimeError(f"音色转换失败: {convert_resp.status_code} {convert_resp.text}")

        # 保存返回的音频到临时文件
        output_path = audio_path.replace(".wav", "_converted.wav")
        with open(output_path, "wb") as f:
            f.write(convert_resp.content)

        logger.info(f"音色转换完成: {output_path}")
        return output_path

    def tts(self, text: str, reference_id: str = None) -> bytes:
        """
        语音合成：把文本转成目标音色的语音
        :param text: 要合成的文本
        :param reference_id: 目标音色 ID
        :return: 音频二进制数据
        """
        if not self.api_key:
            raise ValueError("Fish Audio API Key 未配置")

        ref_id = reference_id or self.reference_id
        url = f"{self.base_url}/v1/tts"
        payload = {
            "text": text,
            "reference_id": ref_id,
            "format": "wav",
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=120)

        if resp.status_code != 200:
            raise RuntimeError(f"TTS 失败: {resp.status_code} {resp.text}")

        return resp.content