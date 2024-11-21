from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.log import logger
from sqlmodel import Session, select
import re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
from typing import Tuple

from ..database import get_session, ArkAccount, ArkConfig

class ConfigImageGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.assets_dir = self.base_dir / "assets"
        self.cache_dir = self.assets_dir / "cache"
        self.fonts_dir = self.assets_dir / "fonts"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':  # 如果不是Windows系统
            os.chmod(str(self.cache_dir), 0o755)

        self.font_path = str(self.fonts_dir / "SarasaMonoSC-Regular.ttf")
        try:
            self.title_font = ImageFont.truetype(self.font_path, 32)
            self.header_font = ImageFont.truetype(self.font_path, 24)
            self.content_font = ImageFont.truetype(self.font_path, 20)
        except Exception as e:
            logger.error(f"Failed to load font: {str(e)}")
            raise
        
        self.background_color = (255, 255, 255)
        self.title_color = (51, 51, 51)
        self.header_color = (64, 158, 255)
        self.text_color = (102, 102, 102)
        self.checkbox_color = (0, 122, 255)
        self.checkbox_bg = (240, 240, 240)

    def get_masked_username(self, username: str) -> str:
        if len(username) <= 5:
            return username
        return username[:5] + "***"

    def draw_checkbox(self, draw: ImageDraw.ImageDraw, x: float, y: float, checked: bool, size: int = 16) -> None:
        x_int = int(x)
        y_int = int(y)
        
        draw.rectangle(
            [x_int, y_int, x_int + size, y_int + size],
            fill=self.checkbox_bg,
            outline=self.checkbox_color
        )
        
        if checked:
            padding = size // 4
            draw.line(
                [
                    (x_int + padding, y_int + size//2),
                    (x_int + size//2, y_int + size - padding),
                    (x_int + size - padding, y_int + padding)
                ],
                fill=self.checkbox_color,
                width=2
            )

    def get_text_size(self, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        left, top, right, bottom = font.getbbox(text)
        return (int(right - left), int(bottom - top))

    def create_config_image(self, account: ArkAccount, config: ArkConfig) -> Image.Image:
        padding = 30
        line_spacing = 12
        section_spacing = 20
        checkbox_size = 16
        width = 600

        img = Image.new('RGB', (width, 2000), self.background_color)
        draw = ImageDraw.Draw(img)
        
        current_y = padding

        title = f"账号#{account.account_index} 配置信息"
        title_w = self.get_text_size(title, self.title_font)[0]
        draw.text((width//2 - title_w//2, current_y), title, 
                font=self.title_font, fill=self.title_color)
        current_y += self.title_font.size + section_spacing//2

        draw.text((padding, current_y), "【基本信息】", 
                font=self.header_font, fill=self.header_color)
        current_y += self.header_font.size + line_spacing

        masked_username = self.get_masked_username(account.username)
        basic_info = [
            f"账号：{masked_username}",
            f"设备号：{account.device or '未设置'}",
            f"服务器：{'B服' if account.server == 'bilibili' else '官服'}",
            f"作战关卡：{config.fight_stages}",
            f"吃理智药：{config.max_drug_times}次",
            f"吃源石：{config.max_stone_times}次"
        ]
        
        for info in basic_info:
            text_h = self.get_text_size(info, self.content_font)[1]
            draw.text((padding + 15, current_y), info, 
                    font=self.content_font, fill=self.text_color)
            current_y += text_h + line_spacing
            
        current_y += section_spacing//2

        draw.text((padding, current_y), "【商店配置】", 
                font=self.header_font, fill=self.header_color)
        current_y += self.header_font.size + line_spacing
        
        shop_config = config.shop_config or {}
        shop_info = [
            f"信用多买：{shop_config.get('high_priority', '未设置')}",
            f"信用少买：{shop_config.get('low_priority', '未设置')}"
        ]
        
        for info in shop_info:
            text_h = self.get_text_size(info, self.content_font)[1]
            draw.text((padding + 15, current_y), info, 
                    font=self.content_font, fill=self.text_color)
            current_y += text_h + line_spacing
            
        current_y += section_spacing//2

        draw.text((padding, current_y), "【公招配置】", 
                font=self.header_font, fill=self.header_color)
        current_y += self.header_font.size + line_spacing
        
        recruit_config = config.auto_recruit_config or {}
        recruit_items = [
            ("其他标签", "auto_recruit0"),
            ("支援机械", "auto_recruit1"),
            ("4星干员", "auto_recruit4"),
            ("5星干员", "auto_recruit5"),
            ("6星干员", "auto_recruit6")
        ]

        recruit_start_y = current_y
        col_width = (width - 2 * padding) // 2

        left_items = recruit_items[:3]
        right_items = recruit_items[3:]

        for i, (label, key) in enumerate(left_items):
            y = recruit_start_y + i * (checkbox_size + line_spacing)
            checked = recruit_config.get(key, True)
            self.draw_checkbox(draw, padding + 15, y + 2, checked, checkbox_size)
            draw.text((padding + 15 + checkbox_size + 8, y), 
                    label, font=self.content_font, fill=self.text_color)

        for i, (label, key) in enumerate(right_items):
            y = recruit_start_y + i * (checkbox_size + line_spacing)
            x = padding + 15 + col_width
            checked = recruit_config.get(key, True)
            self.draw_checkbox(draw, x, y + 2, checked, checkbox_size)
            draw.text((x + checkbox_size + 8, y), 
                    label, font=self.content_font, fill=self.text_color)

        current_y = recruit_start_y + (max(len(left_items), len(right_items)) * (checkbox_size + line_spacing))
        current_y += section_spacing//2

        draw.text((padding, current_y), "【任务配置】", 
                font=self.header_font, fill=self.header_color)
        current_y += self.header_font.size + line_spacing
        
        task_config = config.task_config or {}
        task_items = [
            ("邮件收取", "collect_mail"),
            ("轮次作战", "battle_loop"),
            ("自动培养", "auto_recruit"),
            ("访问好友", "visit_friends"),
            ("基建收获", "base_collect"),
            ("基建换班", "base_shift"),
            ("制造加速", "manufacture_boost"),
            ("线索交流", "clue_exchange"),
            ("副手换人", "deputy_change"),
            ("信用购买", "credit_shop"),
            ("公开招募", "public_recruit"),
            ("任务收集", "mission_collect"),
            ("限时活动", "time_limited"),
            ("商店搬空", "shop_purchase"),
            ("故事解锁", "story_unlock"),
            ("森空岛签到", "skland_checkin")
        ]
        
        task_start_y = current_y
        items_per_col = (len(task_items) + 1) // 2

        left_tasks = task_items[:items_per_col]
        right_tasks = task_items[items_per_col:]

        for i, (label, key) in enumerate(left_tasks):
            y = task_start_y + i * (checkbox_size + line_spacing)
            checked = task_config.get(key, True)
            self.draw_checkbox(draw, padding + 15, y + 2, checked, checkbox_size)
            draw.text((padding + 15 + checkbox_size + 8, y), 
                    label, font=self.content_font, fill=self.text_color)

        for i, (label, key) in enumerate(right_tasks):
            y = task_start_y + i * (checkbox_size + line_spacing)
            x = padding + 15 + col_width
            checked = task_config.get(key, True)
            self.draw_checkbox(draw, x, y + 2, checked, checkbox_size)
            draw.text((x + checkbox_size + 8, y), 
                    label, font=self.content_font, fill=self.text_color)

        final_height = task_start_y + (max(len(left_tasks), len(right_tasks)) * (checkbox_size + line_spacing))
        final_height += padding

        img = img.crop((0, 0, width, final_height))
        
        return img

    def get_config_image(self, account: ArkAccount, config: ArkConfig) -> str:
        cache_file = self.cache_dir / f"config_{account.account_index}_{account.username}.png"
        
        try:
            config_image = self.create_config_image(account, config)
            config_image.save(str(cache_file))
            if os.name != 'nt':  # 如果不是Windows系统
                os.chmod(str(cache_file), 0o644)
            return str(cache_file)
        except Exception as e:
            logger.error(f"Failed to generate config image: {str(e)}")
            raise

ark_config = on_regex(r"^账号配置\s*(\d+)$", priority=5)

@ark_config.handle()
async def handle_config(event: MessageEvent):
    try:
        msg = str(event.get_message()).strip()
        match = re.match(r"^账号配置\s*(\d+)$", msg)
        if not match:
            await ark_config.finish("命令格式错误！\n格式：账号配置 序号")
            return

        account_index = int(match.group(1))
        
        with get_session() as session:
            account = session.exec(
                select(ArkAccount).where(
                    ArkAccount.qq == str(event.user_id),
                    ArkAccount.account_index == account_index
                )
            ).first()
            
            if not account:
                await ark_config.finish(f"未找到序号为 {account_index} 的账号")
                return
            
            config = session.exec(
                select(ArkConfig).where(
                    ArkConfig.username == account.username
                )
            ).first()
            
            if not config:
                config = ArkConfig(username=account.username)
                session.add(config)
                session.commit()

            image_generator = ConfigImageGenerator()
            image_path = image_generator.get_config_image(account, config)
            
            if not os.path.exists(image_path):
                await ark_config.finish("生成配置图片失败，请联系管理员")
                return

            relative_path = str(Path(image_path).resolve())
            
            try:
                await ark_config.send(MessageSegment.image(file=f"file://{relative_path}"))
            except Exception as first_error:
                try:
                    await ark_config.send(MessageSegment.image(file=relative_path))
                except Exception as second_error:
                    await ark_config.send("图片发送失败，请检查文件权限或联系管理员")
            
            try:
                os.remove(image_path)
            except Exception as e:
                logger.warning(f"Failed to remove cache file: {e}")

    except Exception as e:
        logger.error(f"Error in handle_config: {e}")
        await ark_config.finish(f"获取配置失败：{str(e)}")