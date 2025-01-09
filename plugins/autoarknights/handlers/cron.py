import asyncio
import nonebot
from nonebot import on_command, require, get_driver
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from datetime import datetime
from sqlmodel import Session, select, distinct
from typing import List, Set, Optional, Tuple, Union
import subprocess
from pathlib import Path

# 导入数据模型和配置
from ..database import ArkAccount, engine
from ..config import arknight_update_times as update_times 

# 注册定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler

# 获取 dlt.py 的路径
DLT_PATH = Path(__file__).parent.parent / "cron" / "dlt.py"

class AccountManager:
    @staticmethod
    async def get_devices() -> List[int]:
        """获取所有不重复的设备号"""
        try:
            with Session(engine) as session:
                statement = select(ArkAccount.device).distinct()
                results = session.exec(statement).all()
                return sorted(list(set(dev for dev in results if dev is not None)))
        except Exception as e:
            logger.error(f"Error getting devices: {str(e)}")
            return []

    @staticmethod
    async def start_fight(device: Union[str, int], accounts: Optional[str] = None) -> Tuple[bool, str]:
        """开始战斗
        Args:
            device: 设备编号
            accounts: 可选，指定账号序号，支持以下格式：
                     - 单个账号："2"
                     - 连续范围："2-4"
                     - 多个账号："2 4 6"
                     - 混合方式："1-3 5 7-9"
        """
        try:
            cmd = ["python", str(DLT_PATH), "mode", str(device), "restart"]
            
            if accounts:
                cmd.append(accounts)
                
            logger.info(f"Starting fight on device {device} with accounts: {accounts}")
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"Failed to start fight on device {device}: {stderr.decode()}")
                return False, f"启动战斗失败: {stderr.decode()}"
            
            logger.info(f"Successfully started fight on device {device}")
            message = f"战斗已启动"
            if accounts:
                message += f"（账号: {accounts}）"
            return True, message
                
        except Exception as e:
            logger.error(f"Error starting fight on device {device}: {str(e)}")
            return False, f"启动战斗时发生错误: {str(e)}"

    @staticmethod
    async def update_accounts() -> Tuple[bool, str]:
        try:
            all_devices = await AccountManager.get_devices()
            if not all_devices:
                return False, "未找到可用设备"

            total_success = 0
            total_fail = 0
            response_messages: List[str] = []
            
            for device in all_devices:
                try:
                    sync_cmd = [
                        "python", str(DLT_PATH),
                        "mode", str(device),
                        "sync_db_config"
                    ]
                    
                    logger.info(f"Syncing config for device {device}")
                    result = subprocess.run(sync_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        total_success += 1
                        msg = f"设备 {device}: 配置同步成功"
                    else:
                        total_fail += 1
                        msg = f"设备 {device}: 配置同步失败: {result.stderr}"
                    
                    response_messages.append(msg)
                    logger.info(msg)
                    
                except Exception as e:
                    total_fail += 1
                    error_msg = f"设备 {device} 更新失败: {str(e)}"
                    response_messages.append(error_msg)
                    logger.error(error_msg)
                    continue
            
            final_message = "\n".join([
                f"总计: 成功{total_success}个设备, 失败{total_fail}个设备",
                "详细信息:",
                *response_messages
            ])
            
            return True, final_message
                        
        except Exception as e:
            error_msg = f"更新过程发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    async def take_screenshot(device: Union[str, int]) -> Tuple[bool, str]:
        """获取设备截图"""
        try:
            cmd = ["python", str(DLT_PATH), "mode", str(device), "screenshot"]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"Failed to take screenshot on device {device}: {stderr.decode()}")
                return False, f"获取截图失败: {stderr.decode()}"
            
            logger.info(f"Successfully took screenshot on device {device}")
            return True, "截图已获取"
                
        except Exception as e:
            logger.error(f"Error taking screenshot on device {device}: {str(e)}")
            return False, f"获取截图时发生错误: {str(e)}"

# 注册定时任务
for update_time in update_times:
    hour, minute = update_time.split(":")
    
    @scheduler.scheduled_job("cron", hour=int(hour), minute=int(minute))
    async def scheduled_update() -> None:
        """定时更新任务"""
        try:
            logger.info(f"Starting scheduled account update at {datetime.now()}")
            success, msg = await AccountManager.update_accounts()
            logger.info(f"Scheduled update completed: {msg}")
            
            await asyncio.sleep(30)
            
            logger.info(f"Starting fights at {datetime.now()}")
            device_list = await AccountManager.get_devices()
            if device_list:
                for dev in device_list:
                    try:
                        success, msg = await AccountManager.start_fight(dev)
                        logger.info(f"Fight started on device {dev}: {msg}")
                        await asyncio.sleep(10)
                    except Exception as e:
                        logger.error(f"Error starting fight on device {dev}: {str(e)}")
                        continue
            
        except Exception as e:
            logger.error(f"Error in scheduled update: {str(e)}")
            return

# 命令处理器
update_handler = on_command("updateall", aliases={"更新所有账号"}, permission=SUPERUSER, priority=5)
fight_handler = on_command("fight", aliases={"一键战斗"}, permission=SUPERUSER, priority=5)
device_handler = on_command("devices", aliases={"获取设备"}, permission=SUPERUSER, priority=5)
screenshot_handler = on_command("screenshot", aliases={"获取截图"}, permission=SUPERUSER, priority=5)
command_handler = on_command("exec", permission=SUPERUSER, priority=5)

@device_handler.handle()
async def handle_devices(event: MessageEvent) -> None:
    """查看当前用户的设备"""
    devices = await AccountManager.get_devices()
    if not devices:
        await device_handler.finish("当前没有启用的设备")
        return
    
    msg = "当前启用的设备:\n" + "\n".join([f"设备 {d}" for d in devices])
    await device_handler.finish(msg)

@update_handler.handle()
async def handle_update(event: MessageEvent) -> None:
    """处理更新命令"""
    await update_handler.send("开始更新账号信息...")
    success, msg = await AccountManager.update_accounts()
    await update_handler.finish(msg)

@fight_handler.handle()
async def handle_fight(event: MessageEvent) -> None:
    """处理战斗命令"""
    args = str(event.get_message()).strip().split()
    if len(args) <= 1:
        await fight_handler.finish(
            "用法：/一键战斗 <设备号> [账号序号]\n"
            "示例：\n"
            "  /fight 1          # 启动设备1的所有账号\n"
            "  /fight 1 2-4      # 启动设备1的2到4号账号\n"
            "  /fight 1 2 4 6    # 启动设备1的2、4、6号账号\n"
            "  /fight 1 1-3 5 7  # 启动设备1的1-3号和5、7号账号"
        )
        return
        
    device = args[1]
    devices = await AccountManager.get_devices()
    if int(device) not in devices:
        await fight_handler.finish(f"设备 {device} 未启用或不存在")
        return
    
    accounts = " ".join(args[2:]) if len(args) > 2 else None
    success, msg = await AccountManager.start_fight(device, accounts)
    await fight_handler.finish(msg)

@command_handler.handle()
async def handle_command(event: MessageEvent) -> None:
    """处理通用命令"""
    msg = str(event.get_message()).strip()
    cmd = msg[4:].strip()  # 去除"exec"前缀
    
    if not cmd:
        await command_handler.finish("请输入要执行的命令")
        return
    
    try:
        logger.info(f"Executing command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        output = result.stdout if result.stdout else result.stderr
        if output:
            # Telegram 消息长度限制为 4096 字符
            if len(output) > 4000:
                for i in range(0, len(output), 4000):
                    await command_handler.send(output[i:i+4000])
            else:
                await command_handler.send(output)
    
    except Exception as e:
        await command_handler.finish(f"执行出错: {str(e)}")
        return
    
    await command_handler.finish("执行完成")

@screenshot_handler.handle()
async def handle_screenshot(event: MessageEvent) -> None:
    """处理截图命令"""
    args = str(event.get_message()).strip().split()
    if len(args) <= 1:
        await screenshot_handler.finish("用法：/screenshot <设备号>")
        return
        
    device = args[1]
    
    try:
        devices = await AccountManager.get_devices()
        if int(device) not in devices:
            await screenshot_handler.finish(f"设备 {device} 未启用或不存在")
            return
            
        success, msg = await AccountManager.take_screenshot(device)
        await screenshot_handler.finish(msg)
            
    except Exception as e:
        logger.error(f"Screenshot error: {str(e)}")
        await screenshot_handler.finish(f"执行出错: {str(e)}")
