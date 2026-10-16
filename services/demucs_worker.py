# services/demucs_worker.py
import os
import numpy as np
import onnxruntime as ort
import soundfile as sf
import librosa
from astrbot.api import logger


class MDXSeparator:
    def __init__(self, model_path: str, model_name: str = "htdemucs"):
        """
        初始化 UVR5 MDX 人声分离器
        :param model_path: .onnx 模型文件的完整路径
        :param model_name: 配置里传进来的模型名（用于日志和兼容）
        """
        self.model_path = model_path
        self.model_name = model_name

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"找不到 MDX 模型文件: {model_path}")

        # 初始化 ONNX Runtime 会话
        # CPUExecutionProvider 是纯 CPU 推理，如果有 GPU 可以换成 CUDAExecutionProvider
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )

        # 获取模型输入输出的名称
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]

    def separate(self, audio_path: str, output_dir: str) -> tuple[str, str]:
        """
        分离人声和伴奏
        :param audio_path: 输入音频路径
        :param output_dir: 输出目录
        :return: (人声文件路径, 伴奏文件路径)
        """
        logger.info(f"正在分离人声/伴奏: {audio_path}")

        # 1. 读取音频，统一重采样到 44100Hz，MDX 模型通常要求这个采样率
        audio, sr = librosa.load(audio_path, sr=44100, mono=False)
        if audio.ndim == 1:
            audio = np.stack([audio, audio], axis=0)  # 单声道转双声道

        # 2. 转成模型需要的形状和数据类型（通常要求 float32）
        # MDX 模型一般输入形状为 [batch, channels, samples]
        input_audio = audio.astype(np.float32)

        # 3. 推理，得到人声分量
        logger.info("正在推理分离...")
        vocals_pred = self.session.run(
            self.output_names,
            {self.input_name: input_audio}
        )[0]

        # 4. 计算伴奏 = 原始音频 - 人声
        # 把推理结果调整回和原音频一样的形状
        vocals = np.squeeze(vocals_pred, axis=0) if vocals_pred.ndim == 3 else vocals_pred
        accompaniment = audio - vocals

        # 5. 保存为 wav 文件
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        vocals_path = os.path.join(output_dir, f"{base_name}_vocals.wav")
        accompaniment_path = os.path.join(output_dir, f"{base_name}_accompaniment.wav")

        # 转置回 [samples, channels] 再保存，soundfile 要求这个形状
        sf.write(vocals_path, vocals.T, sr)
        sf.write(accompaniment_path, accompaniment.T, sr)

        logger.info(f"分离完成: 人声={vocals_path}, 伴奏={accompaniment_path}")
        return vocals_path, accompaniment_path


        separator = MDXSeparator(model_path, model_name)
        return separator.separate(audio_path, output_dir)