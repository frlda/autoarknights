# freeze.py
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.params import CommandArg
from nonebot.log import logger

from ..database.database_manager import FreezeManager

# 注册命令
freeze_account = on_command("冻结账号", priority=5, block=True)
unfreeze_account = on_command("解冻账号", priority=5, block=True)

@freeze_account.handle()
async def handle_freeze(event: MessageEvent, args: Message = CommandArg()):
    """处理账号冻结命令"""
    qq_id = str(event.get_user_id())
    
    try:
        account_index = args.extract_plain_text().strip()
        if not account_index:
            await freeze_account.send("请提供要冻结的账号序号！\n格式：冻结账号 序号")
            return
            
        try:
            account_index = int(account_index)
        except ValueError:
            await freeze_account.send("账号序号必须是数字！")
            return
            
        # 使用FreezeManager冻结账号
        account, message = FreezeManager.freeze_account(qq_id, account_index)
        if not account:
            await freeze_account.send(message)
            return
            
        msg = f"""账号已冻结！
账号：{account.username}
序号：{account_index}
服务器：{'官服' if account.server == 'official' else 'B服'}
状态：已冻结"""
        
        logger.info(f"User {qq_id} froze account {account.username}")
        await freeze_account.send(msg)
            
    except Exception as e:
        logger.error(f"Error in freeze_account: {e}")
        await freeze_account.send(f"冻结账号失败：{str(e)}")

@unfreeze_account.handle()
async def handle_unfreeze(event: MessageEvent, args: Message = CommandArg()):
    """处理账号解冻命令"""
    qq_id = str(event.get_user_id())
    
    try:
        account_index = args.extract_plain_text().strip()
        if not account_index:
            await unfreeze_account.send("请提供要解冻的账号序号！\n格式：解冻账号 序号")
            return
            
        try:
            account_index = int(account_index)
        except ValueError:
            await unfreeze_account.send("账号序号必须是数字！")
            return
            
        # 使用FreezeManager解冻账号
        account, message = FreezeManager.unfreeze_account(qq_id, account_index)
        if not account:
            await unfreeze_account.send(message)
            return
                
        msg = f"""账号已解冻！
账号：{account.username}
序号：{account_index}
服务器：{'官服' if account.server == 'official' else 'B服'}
状态：正常"""
        
        logger.info(f"User {qq_id} unfroze account {account.username}")
        await unfreeze_account.send(msg)
            
    except Exception as e:
        logger.error(f"Error in unfreeze_account: {e}")
        await unfreeze_account.send(f"解冻账号失败：{str(e)}")