import sys
import base64
import asyncio
from typing import Optional, Union
from quart import Quart, request
from nonebot import get_driver, get_bot, require
from nonebot.log import logger
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.message import MessageSegment
from sqlmodel import select, Session
from .database import ArkAccount, engine
from pathlib import Path
import tempfile

require("nonebot_plugin_apscheduler")
driver = get_driver()

HOST = getattr(driver.config, "imagedeliver_host", "0.0.0.0")
PORT = getattr(driver.config, "imagedeliver_port", 8888)

app = Quart(__name__)

async def get_user_by_username(username: str) -> Optional[str]:
    """通过方舟账号用户名获取用户ID"""
    try:
        with Session(engine) as session:
            stmt = select(ArkAccount).where(ArkAccount.username == username)
            account = session.exec(stmt).first()
            if account:
                logger.info(f"Found user {account.user_id} for username {username}")
                return account.user_id
            logger.warning(f"No user found for username {username}")
            return None
    except Exception as e:
        logger.error(f"Database error in get_user_by_username: {str(e)}")
        return None

def mask_username(username: str) -> str:
    """对账号名进行遮蔽处理，保留首尾各2个字符"""
    if len(username) <= 4: 
        return username
    return f"{username[:2]}{'*' * (len(username)-4)}{username[-2:]}"

async def send_telegram_message(
    bot: Bot, 
    chat_id: Union[int, str], 
    text: Optional[str] = None, 
    image_data: Optional[bytes] = None
) -> bool:
    """发送Telegram消息"""
    try:
        # 发送文本消息
        if text:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
            except Exception as e:
                logger.error(f"Failed to send text message: {e}")
                return False

        # 发送图片
        if image_data:
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp.write(image_data)
                    tmp_path = Path(tmp.name)

                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=image_data
                    )
                finally:
                    # 清理临时文件
                    if tmp_path.exists():
                        tmp_path.unlink()
            except Exception as e:
                logger.error(f"Failed to send image: {e}")
                return False

        return True

    except Exception as e:
        logger.error(f"Error in send_telegram_message: {e}")
        return False

@app.post("/")
async def handle_message():
    """处理消息接收端点"""
    try:
        form = await request.form
        to = form.get("to")
        info = form.get("info", "")
        image_b64 = form.get("image", "")
        
        if not to or (not info and not image_b64):
            return {"status": "error", "message": "Missing parameters"}

        # 处理文本信息
        final_info = None
        if info:
            logger.info(f"Received info: {info}")
            words = info.split()
            new_info = []
            for word in words:
                user_id = await get_user_by_username(word)
                if user_id:
                    masked_username = mask_username(word)
                    logger.info(f"Converting username {word} to {masked_username}(ID:{user_id})")
                    new_info.append(f"{masked_username}(ID:{user_id})")
                else:
                    logger.info(f"Keeping original word: {word}")
                    new_info.append(word)
            
            final_info = " ".join(new_info)
            logger.info(f"Final processed info: {final_info}")

        # 处理图片
        image_data = None
        if image_b64:
            try:
                image_data = base64.b64decode(image_b64)
                logger.info("Successfully decoded base64 image")
            except Exception as e:
                logger.error(f"Image processing error: {str(e)}")
                return {"status": "error", "message": "Invalid image"}

        try:
            bot = get_bot()
            if not isinstance(bot, Bot):
                raise ValueError("Not a Telegram bot instance")
        except Exception as e:
            logger.error(f"Failed to get bot: {e}")
            return {"status": "error", "message": "Bot not available"}

        try:
            # 解析发送目标ID
            if to.startswith('g'):
                chat_id = int(to[1:])  # 群组ID
                logger.info(f"Sending to group: {chat_id}")
            else:
                chat_id = int(to)      # 用户ID
                logger.info(f"Sending to user: {chat_id}")
            
            # 发送消息
            if final_info:
                success = await send_telegram_message(bot, chat_id, text=final_info)
                if not success:
                    return {"status": "error", "message": "Failed to send text message"}
            
            if image_data:
                success = await send_telegram_message(bot, chat_id, image_data=image_data)
                if not success:
                    return {"status": "error", "message": "Failed to send image"}
            
            return {"status": "success"}
            
        except ValueError as e:
            logger.error(f"Invalid chat ID: {e}")
            return {"status": "error", "message": "Invalid chat ID"}
        except Exception as e:
            logger.error(f"Message sending error: {str(e)}")
            return {"status": "error", "message": str(e)}

    except Exception as e:
        logger.error(f"General error in handle_message: {str(e)}")
        return {"status": "error", "message": str(e)}

def run_server():
    """启动服务器"""
    logger.info(f"Starting Image Deliver server at http://{HOST}:{PORT}")
    
    sys.dont_write_bytecode = True
    asyncio.create_task(
        app.run_task(
            host=HOST,
            port=PORT,
        )
    )

@driver.on_startup
async def _():
    run_server()