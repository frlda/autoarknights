import sys
import base64
import asyncio
from typing import Optional
from quart import Quart, request
from nonebot import get_driver, get_bot, require
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from sqlmodel import select, Session
from .database import ArkAccount, engine

require("nonebot_plugin_apscheduler")
driver = get_driver()


HOST = getattr(driver.config, "imagedeliver_host", "0.0.0.0")
PORT = getattr(driver.config, "imagedeliver_port", 8888)

app = Quart(__name__)

def get_qq_by_username(username: str) -> Optional[str]:
    """通过方舟账号用户名获取QQ号"""
    try:
        with Session(engine) as session:
            stmt = select(ArkAccount).where(ArkAccount.username == username)
            account = session.exec(stmt).first()
            if account:
                logger.info(f"Found QQ {account.qq} for username {username}")
                return account.qq
            logger.warning(f"No QQ found for username {username}")
            return None
    except Exception as e:
        logger.error(f"Database error in get_qq_by_username: {str(e)}")
        return None


def mask_username(username: str) -> str:
    """对账号名进行遮蔽处理，保留首尾各2个字符"""
    if len(username) <= 4: 
        return username
    
    # 保留首尾各2个字符，中间用*替代
    return f"{username[:2]}{'*' * (len(username)-4)}{username[-2:]}"

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

        msg = Message()
        if info:
            logger.info(f"Received info: {info}")
            
            # 分割信息，检查每个部分是否是账号名
            words = info.split()
            new_info = []
            for word in words:
                qq = get_qq_by_username(word)
                if qq:
                    # 如果找到QQ号，添加遮蔽后的账号名和QQ号
                    masked_username = mask_username(word)
                    logger.info(f"Converting username {word} to {masked_username}(QQ:{qq})")
                    new_info.append(f"{masked_username}(QQ:{qq})")
                else:
                    logger.info(f"Keeping original word: {word}")
                    new_info.append(word)
            
            # 将处理后的信息组合起来
            final_info = " ".join(new_info)
            logger.info(f"Final processed info: {final_info}")
            msg += MessageSegment.text(final_info)

        if image_b64:
            try:
                msg += MessageSegment.image(f"base64://{image_b64}")
            except Exception as e:
                logger.error(f"Image processing error: {str(e)}")
                return {"status": "error", "message": "Invalid image"}

        bot = get_bot()
        try:
            if to.startswith('g'):
                group_id = int(to[1:])
                logger.info(f"Sending message to group {group_id}")
                await bot.send_group_msg(group_id=group_id, message=msg)
            else:
                user_id = int(to)
                logger.info(f"Sending message to user {user_id}")
                await bot.send_private_msg(user_id=user_id, message=msg)
            return {"status": "success"}
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