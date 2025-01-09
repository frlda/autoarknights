from nonebot import on_command
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.params import CommandArg
from nonebot.adapters.telegram.message import Message
from nonebot.permission import SUPERUSER
from ..database.database_manager import DeviceManager, get_session

bind_device = on_command("bind_device", aliases={"绑定设备"}, priority=5)
unbind_device = on_command("unbind_device", aliases={"解绑设备"}, priority=5)
list_devices = on_command("list_devices", aliases={"设备列表"}, permission=SUPERUSER, priority=5, block=True)

@bind_device.handle()
async def handle_bind_device(event: MessageEvent, args: Message = CommandArg()):
    """处理绑定设备命令"""
    user_id = str(event.get_user_id())
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await bind_device.finish("请提供账号序号和设备号！\n格式：/bind_device <账号序号> <设备号>")
            return

        args_list = args_text.split()
        if len(args_list) != 2:
            await bind_device.finish("参数格式错误！\n格式：/bind_device <账号序号> <设备号>")
            return
            
        try:
            account_index = int(args_list[0])
            device_id = int(args_list[1])
        except ValueError:
            await bind_device.finish("账号序号和设备号必须是数字！")
            return
            
        account, msg = DeviceManager.set_device(
            user_id=user_id,
            account_index=account_index,
            device_id=device_id
        )
        
        if account:
            msg = f"""设备绑定成功！
账号：{account.username}
序号：{account.account_index}
设备号：{account.device}"""
            
        await bind_device.finish(msg)
            
    except Exception as e:
        await bind_device.finish(f"设备绑定结果：{str(e)}")

@unbind_device.handle()
async def handle_unbind_device(event: MessageEvent, args: Message = CommandArg()):
    """处理解绑设备命令"""
    user_id = str(event.get_user_id())
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await unbind_device.finish("请提供账号序号！\n格式：/unbind_device <账号序号>")
            return

        try:
            account_index = int(args_text)
        except ValueError:
            await unbind_device.finish("账号序号必须是数字！")
            return
            
        account, msg = DeviceManager.remove_device(
            user_id=user_id,
            account_index=account_index
        )
        
        if account:
            msg = f"""设备解绑成功！
账号：{account.username}
序号：{account.account_index}"""
            
        await unbind_device.finish(msg)
            
    except Exception as e:
        await unbind_device.finish(f"设备解绑失败：{str(e)}")

@list_devices.handle()
async def handle_list_devices(event: MessageEvent):
    """处理查看设备列表命令"""
    try:
        with get_session() as session:
            device_usage = DeviceManager.get_device_usage(session)
            
            if not device_usage:
                await list_devices.finish("当前没有设备被使用")
                return
                
            msg = "设备使用情况：\n"
            for device_id, accounts in device_usage.items():
                msg += f"\n设备 {device_id}："
                for account in accounts:
                    msg += f"\n- {account.username} (用户 {account.user_id} 的第 {account.account_index} 个账号)"
                msg += "\n"
                
            await list_devices.finish(msg)
            
    except Exception as e:
        await list_devices.finish(f"获取设备列表获取结果：{str(e)}")
