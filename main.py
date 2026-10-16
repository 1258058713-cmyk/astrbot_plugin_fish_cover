# main.py
from .services.limit_service import DailyLimitService
import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
import astrbot.api.message_components as Comp
from .services.cover_service import CoverService
import os

class FishCoverPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = context.get_config()
        fish_api_key = self.config.get("fish_api_key", "")
        plugin_dir = os.path.dirname(__file__)
        model_path = os.path.join(plugin_dir, "models", "UVR-MDX-NET-Inst_HQ_3.onnx")

        self.cover_service = CoverService(
            fish_api_key=fish_api_key,
            model_path=model_path
        )
        daily_limit = self.config.get("daily_limit", 5)
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        self.limit_service = DailyLimitService(data_dir, daily_limit)


    @filter.command("翻唱")
    async def cover(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if not self.limit_service.check_and_add(user_id):
            remaining = self.limit_service.get_remaining(user_id)
            yield event.plain_result(
                f"你今天已经用完了 {self.daily_limit} 次翻唱机会，明天再来吧～"
            )
            return

        song_name = event.message_str.replace("/翻唱", "").strip()
        if not song_name:
            yield event.plain_result("请在 /翻唱 后面输入歌曲名，例如：/翻唱 世界还未开始")
            return

        remaining = self.limit_service.get_remaining(user_id)
        yield event.plain_result(f"开始处理《{song_name}》，今天你还剩 {remaining} 次")

        try:
            final_audio_path = await self.cover_service.generate_cover(song_name)

            yield event.chain_result([
                Comp.Record(file=final_audio_path, url=final_audio_path)
            ])

        except Exception as e:
            logger.error(f"翻唱失败: {e}")
            yield event.plain_result(f"翻唱处理失败了：{str(e)}")