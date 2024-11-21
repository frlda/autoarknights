import os
import traceback
from nonebot import on_command, get_bot
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.log import logger
from nonebot.exception import FinishedException
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple
from pathlib import Path

help_handler = on_command("方舟help", aliases={"help"}, priority=5, block=True)

class HelpImageGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.assets_dir = self.base_dir / "assets"
        self.cache_dir = self.assets_dir / "cache"
        self.fonts_dir = self.assets_dir / "fonts"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':  # 如果不是Windows系统
            os.chmod(str(self.cache_dir), 0o755)
        
        self.normal_cache = self.cache_dir / "help_normal.png"
        self.admin_cache = self.cache_dir / "help_admin.png"

        self.font_path = str(self.fonts_dir / "SarasaMonoSC-Regular.ttf")
        
        try:
            self.title_font = ImageFont.truetype(self.font_path, 28)
            self.header_font = ImageFont.truetype(self.font_path, 24)
            self.content_font = ImageFont.truetype(self.font_path, 20)
            logger.info("Font loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load font: {str(e)}")
            raise
        
        self.background_color = (255, 255, 255)
        self.title_color = (51, 51, 51)
        self.header_color = (64, 158, 255)
        self.text_color = (102, 102, 102)

    def get_help_content(self, is_admin: bool = False) -> dict:
        content = {
            "title": "明日方舟速通助手",
            "sections": {
                "账号管理": [
                    "/绑定游戏账号 账号 密码 服务器(官服/b服) - 绑定新账号",
                    "/删除游戏账号 账号序号 - 删除绑定的账号",
                    "/查看账号列表 - 查看所有已绑定账号和设置的关卡",
                    "/修改账号信息 账号序号 新账号名 新密码 服务器 - 修改账号信息",
                    "   (若某项不需修改请用'-'代替)"
                ],
                "账号配置": [
                    "/账号设置 账号序号 作战关卡 - 设置账号刷图关卡",
                    "/账号设置 账号序号 邮件收取 - 关闭某一账号邮件收取功能",
                    "/账号配置 账号序号 - 查看账号配置",
                ],
                "设备管理": [
                    "/设置设备 账号序号 设备号 - 设置账号使用的设备",
                    "/查询设备 [账号序号] - 查看账号使用的设备",
                ],
                "账号状态": [
                    "/冻结账号 账号序号 - 暂时停止账号的自动任务",
                    "/解冻账号 账号序号 - 恢复账号的运行状态"
                ],
                "说明": [
                    "1. [] 中的参数为可选参数",
                    "2. 账号序号从1开始，可在【查看账号列表】中查看",
                    "3. 关卡列表格式示例：jm hd",
                ],
                "使用示例": [
                    "1. 绑定账号示例:",
                    "   /绑定游戏账号 test@test.com 123456 官服",
                    "   /绑定游戏账号 12345678 123456 b服",
                    "2. 修改账号示例:",
                    "   /修改账号信息 1 - newpassword -",
                    "   (只修改账号1的密码，账号和服务器不变)",
                    "3. 设置设备示例:",
                    "   /设置设备 1 1",
                    "   (将序号1的账号设置到设备1，一定要绑定设备)",
                    "4. 设置关卡示例:",
                    "   /账号设置 1 作战关卡 jm hd-9",
                    "   (将账号1的刷取关卡设置为剿灭和活动第九关，一定要设置关卡)",
                ],
                "注意事项": [
                    "1. 自己把账号冻结后将从下一(8h)周期暂停所有自动操作",
                    "2. 账号过期会自动冻结",
                    "3. 解冻已过期账号需要先续期",
                    "4. 自动战斗时间为4 12 20 点，八小时一周期，按账号队列进行战斗",
                    "   按账号绑定前后顺序进行战斗，请注意推送信息",
                ]
            }
        }

        if is_admin:
            content["sections"].update({
                "管理员命令": [
                    "/强制删除账号 QQ号 账号序号 - 强制删除指定QQ的账号",
                    "/搜索账号 QQ号 - 搜索指定QQ的所有账号",
                    "/设置设备限制 设备号 限制数量 - 设置设备可绑定的最大账号数",
                    "/更新所有账号 - 更新所有账号的配置",
                    "/一键战斗 设备号 - 启动指定设备的战斗",
                    "/获取设备 - 查看当前启用的设备",
                    "/获取截图 设备号 - 获取指定设备的状态截图"
                ]
            })
        
        return content

    def get_text_size(self, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        left, top, right, bottom = font.getbbox(text)
        return (int(right - left), int(bottom - top))

    def create_help_image(self, content: dict) -> Image.Image:
        padding = 40
        line_spacing = 10
        section_spacing = 30
        
        height = padding * 2
        height += self.get_text_size(content["title"], self.title_font)[1]
        height += section_spacing
        
        max_width = 800
        
        for section, lines in content["sections"].items():
            height += self.get_text_size(section, self.header_font)[1]
            height += line_spacing
            for line in lines:
                height += self.get_text_size(line, self.content_font)[1]
                height += line_spacing
            height += section_spacing

        img = Image.new('RGB', (max_width, height), self.background_color)
        draw = ImageDraw.Draw(img)

        title_size = self.get_text_size(content["title"], self.title_font)
        title_x = (max_width - title_size[0]) // 2
        current_y = padding
        draw.text((title_x, current_y), content["title"], 
                 font=self.title_font, fill=self.title_color)
        current_y += title_size[1] + section_spacing

        for section, lines in content["sections"].items():
            draw.text((padding, current_y), f"【{section}】", 
                     font=self.header_font, fill=self.header_color)
            current_y += self.get_text_size(section, self.header_font)[1] + line_spacing

            for line in lines:
                draw.text((padding + 20, current_y), line, 
                         font=self.content_font, fill=self.text_color)
                current_y += self.get_text_size(line, self.content_font)[1] + line_spacing
            current_y += section_spacing

        return img

    def get_help_image(self, is_admin: bool = False) -> str:
        content = self.get_help_content(is_admin)
        cache_file = self.admin_cache if is_admin else self.normal_cache
        
        try:
            help_image = self.create_help_image(content)
            help_image.save(str(cache_file))
            if os.name != 'nt':  # 如果不是Windows系统
                os.chmod(str(cache_file), 0o644)
            return str(cache_file)
        except Exception as e:
            logger.error(f"Failed to generate help image: {str(e)}")
            raise

@help_handler.handle()
async def handle_help(event: MessageEvent) -> None:
    try:
        bot = get_bot()
        is_admin = str(event.get_user_id()) in bot.config.superusers
        
        help_generator = HelpImageGenerator()
        
        cache_file = help_generator.admin_cache if is_admin else help_generator.normal_cache
        if os.path.exists(str(cache_file)):
            try:
                os.remove(str(cache_file))
                logger.info(f"Removed old cache file: {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to remove cache file: {e}")
        
        image_path = help_generator.get_help_image(is_admin)
        
        if not os.path.exists(image_path):
            logger.error(f"Help image not found at {image_path}")
            await help_handler.send("生成帮助图片失败，请联系管理员。")
            return
            
        # 获取相对路径
        relative_path = str(Path(image_path).resolve())
        
        try:
            # 首先尝试使用file协议
            await help_handler.send(MessageSegment.image(file=f"file://{relative_path}"))
        except Exception as first_error:
            logger.error(f"Failed to send image with file protocol: {first_error}")
            try:
                # 如果失败，尝试直接使用路径
                await help_handler.send(MessageSegment.image(file=relative_path))
            except Exception as second_error:
                logger.error(f"Failed to send image with direct path: {second_error}")
                await help_handler.send("图片发送失败，请联系管理员")
        
    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        await help_handler.send("获取帮助信息失败，请稍后再试。")