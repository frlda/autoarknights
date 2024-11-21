from nonebot import on_command, get_bot
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.params import CommandArg
from nonebot.log import logger
from typing import Dict, List

from ..database.database_manager import DeviceManager
from ..config import MIN_DEVICE, MAX_DEVICE, device_limits
from ..database import get_session, ArkAccount
from sqlmodel import select

# 注册命令
set_device = on_command("设置设备", aliases={"setdevice"}, priority=5, block=True)
query_device = on_command("查询设备", aliases={"device"}, priority=5, block=True)
set_device_limit = on_command("设置设备限制", aliases={"setlimit"}, priority=5, block=True)
query_device_usage = on_command("查看设备使用情况", aliases={"deviceusage"}, priority=5, block=True)

@set_device.handle()
async def handle_set_device(event: MessageEvent, args: Message = CommandArg()):
    """处理设置设备命令"""
    qq_id = str(event.get_user_id())
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            device_list = ", ".join(str(i) for i in range(MIN_DEVICE, MAX_DEVICE + 1))
            await set_device.send(
                f"请提供账号序号和设备号！\n"
                f"格式：设置设备 账号序号 设备号\n"
                f"可用设备号：{device_list}\n"
                f"示例：设置设备 1 2"
            )
            return
            
        args_list = args_text.split()
        if len(args_list) != 2:
            await set_device.send("参数格式错误！请提供账号序号和设备号。")
            return
            
        try:
            account_index = int(args_list[0])
            device_id = int(args_list[1])
        except ValueError:
            await set_device.send("账号序号和设备号都必须是数字！")
            return
            
        if not (MIN_DEVICE <= device_id <= MAX_DEVICE):
            await set_device.send(f"设备号必须在 {MIN_DEVICE} 到 {MAX_DEVICE} 之间！")
            return
            
        # 使用DeviceManager设置设备
        account, message = await DeviceManager.set_device(qq_id, account_index, device_id)
        if not account:
            await set_device.send(message)
            return
            
        with get_session() as session:
            device_usage: Dict[int, List[ArkAccount]] = await DeviceManager.get_device_usage(session)
            current_usage = len(device_usage[device_id])
            device_limit = device_limits[device_id]
            
            msg = f"""已更新设备号！
账号序号：{account_index}
用户名：{account.username}
服务器：{'官服' if account.server == 'official' else 'B服'}
新设备号：{device_id}
当前设备使用情况：{current_usage}/{device_limit}"""
            
            logger.info(f"User {qq_id} set device {device_id} for account {account.username}")
            await set_device.send(msg)
            
    except Exception as e:
        logger.error(f"Error in set_device: {e}")
        await set_device.send(f"设置设备失败：{str(e)}")

@query_device.handle()
async def handle_query_device(event: MessageEvent, args: Message = CommandArg()):
    """处理查询设备命令"""
    qq_id = str(event.get_user_id())
    
    try:
        account_index = args.extract_plain_text().strip()
        
        with get_session() as session:
            device_usage: Dict[int, List[ArkAccount]] = await DeviceManager.get_device_usage(session)
            
            if account_index:
                try:
                    account_index = int(account_index)
                except ValueError:
                    await query_device.send("账号序号必须是数字！")
                    return

                stmt = select(ArkAccount).where(
                    ArkAccount.qq == qq_id,
                    ArkAccount.account_index == account_index
                )
                account = session.exec(stmt).first()
                
                if not account:
                    await query_device.send(f"未找到序号为 {account_index} 的账号！")
                    return

                device_id = account.device
                if device_id is not None:
                    current_usage = len(device_usage[device_id])
                    device_limit = device_limits[device_id]
                    usage_info = f"\n设备使用情况：{current_usage}/{device_limit}"
                else:
                    usage_info = ""

                msg = f"""账号设备信息：
序号：{account.account_index}
用户名：{account.username}
服务器：{'官服' if account.server == 'official' else 'B服'}
当前设备：{account.device if account.device is not None else '未设置'}{usage_info}"""
                
            else:
                # 查询该用户所有账号
                stmt = select(ArkAccount).where(
                    ArkAccount.qq == qq_id
                ).order_by("account_index")
                accounts = list(session.exec(stmt).all())  # 显式转换为 List
                
                if not accounts:
                    await query_device.send("你还没有绑定任何账号！")
                    return

                msg = "账号设备信息：\n"
                for account in accounts:
                    server_name = "官服" if account.server == "official" else "B服"
                    msg += f"{account.account_index}. {account.username} ({server_name})"
                    device_id = account.device
                    if device_id is not None:
                        current_usage = len(device_usage[device_id])
                        device_limit = device_limits[device_id]
                        msg += f" - 设备：{device_id} ({current_usage}/{device_limit})"
                    else:
                        msg += " - 设备：未设置"
                    msg += "\n"
            
            await query_device.send(msg.strip())
            
    except Exception as e:
        logger.error(f"Error in query_device: {e}")
        await query_device.send(f"查询设备失败：{str(e)}")

@set_device_limit.handle()
async def handle_set_limit(event: MessageEvent, args: Message = CommandArg()):
    """处理设置设备限制命令"""
    qq_id = str(event.get_user_id())
    bot = get_bot()
    
    # 检查权限
    if str(qq_id) not in bot.config.superusers:
        await set_device_limit.send("只有管理员才能设置设备使用限制！")
        return
        
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await set_device_limit.send(
                "请提供设备号和限制数量！\n"
                "格式：设置设备限制 设备号 限制数量\n"
                "示例：设置设备限制 1 5"
            )
            return
            
        args_list = args_text.split()
        if len(args_list) != 2:
            await set_device_limit.send("参数格式错误！请提供设备号和限制数量。")
            return
            
        try:
            device_id = int(args_list[0])
            limit = int(args_list[1])
        except ValueError:
            await set_device_limit.send("设备号和限制数量都必须是数字！")
            return
            
        if not (MIN_DEVICE <= device_id <= MAX_DEVICE):
            await set_device_limit.send(f"设备号必须在 {MIN_DEVICE} 到 {MAX_DEVICE} 之间！")
            return
            
        if limit < 1:
            await set_device_limit.send("限制数量必须大于0！")
            return
            
        # 使用DeviceManager设置设备限制
        old_limit, new_limit, current_usage = await DeviceManager.set_device_limit(device_id, limit)
            
        msg = f"""已更新设备使用限制！
设备号：{device_id}
原限制：{old_limit}
新限制：{new_limit}
当前使用：{current_usage}"""
        
        if current_usage > limit:
            msg += f"\n⚠️ 警告：当前使用量超过新限制，请及时调整！"
            
        logger.info(f"Admin {qq_id} set device {device_id} limit to {limit}")
        await set_device_limit.send(msg)
            
    except Exception as e:
        logger.error(f"Error in set_device_limit: {e}")
        await set_device_limit.send(f"设置设备限制失败：{str(e)}")

@query_device_usage.handle()
async def handle_query_usage(event: MessageEvent):
    """处理查询设备使用情况命令"""
    qq_id = str(event.get_user_id())
    bot = get_bot()
    is_admin = str(qq_id) in bot.config.superusers
    
    try:
        with get_session() as session:
            device_usage: Dict[int, List[ArkAccount]] = await DeviceManager.get_device_usage(session)
            
            msg = "设备使用情况：\n"
            for device_id in range(MIN_DEVICE, MAX_DEVICE + 1):
                current_usage = len(device_usage[device_id])
                device_limit = device_limits[device_id]
                
                msg += f"设备 {device_id}：{current_usage}/{device_limit}"
                
                # 管理员可以看到详细信息
                if is_admin and current_usage > 0:
                    accounts = device_usage[device_id]
                    account_info = []
                    for acc in accounts:
                        server = "官服" if acc.server == "official" else "B服"
                        account_info.append(f"{acc.username}({server})")
                    msg += f" - {', '.join(account_info)}"
                    
                msg += "\n"
            
            await query_device_usage.send(msg.strip())
            
    except Exception as e:
        logger.error(f"Error in query_device_usage: {e}")
        await query_device_usage.send(f"查询设备使用情况失败：{str(e)}")