# freeze.py
from nonebot import on_command
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.params import CommandArg
from nonebot.log import logger
from nonebot.adapters.telegram.message import Message

from ..database.database_manager import FreezeManager

# 注册命令
freeze_account = on_command("freeze", aliases={"冻结账号"}, priority=5, block=True)
unfreeze_account = on_command("unfreeze", aliases={"解冻账号"}, priority=5, block=True)

@freeze_account.handle()
async def handle_freeze(event: MessageEvent, args: Message = CommandArg()):
    """处理账号冻结命令"""
    user_id = str(event.get_user_id())
    
    try:
        account_index = args.extract_plain_text().strip()
        if not account_index:
            await freeze_account.finish("请提供要冻结的账号序号！\n格式：/freeze <序号>")
            return
            
        try:
            account_index = int(account_index)
        except ValueError:
            await freeze_account.finish("账号序号必须是数字！")
            return
            
        # 使用FreezeManager冻结账号
        account, message = FreezeManager.freeze_account(user_id, account_index)
        if not account:
            await freeze_account.finish(message)
            return
            
        msg = f"""账号已冻结！
账号：{account.username}
序号：{account_index}
服务器：{'官服' if account.server == 'official' else 'B服'}
状态：已冻结"""
        
        logger.info(f"User {user_id} froze account {account.username}")
        await freeze_account.finish(msg)
            
    except Exception as e:
        logger.error(f"Error in freeze_account: {e}")
        await freeze_account.finish(f"冻结账号失败：{str(e)}")

@unfreeze_account.handle()
async def handle_unfreeze(event: MessageEvent, args: Message = CommandArg()):
    """处理账号解冻命令"""
    user_id = str(event.get_user_id())
    
    try:
        account_index = args.extract_plain_text().strip()
        if not account_index:
            await unfreeze_account.finish("请提供要解冻的账号序号！\n格式：/unfreeze <序号>")
            return
            
        try:
            account_index = int(account_index)
        except ValueError:
            await unfreeze_account.finish("账号序号必须是数字！")
            return
            
        # 使用FreezeManager解冻账号
        account, message = FreezeManager.unfreeze_account(user_id, account_index)
        if not account:
            await unfreeze_account.finish(message)
            return
                
        msg = f"""账号已解冻！
账号：{account.username}
序号：{account_index}
服务器：{'官服' if account.server == 'official' else 'B服'}
状态：正常"""
        
        logger.info(f"User {user_id} unfroze account {account.username}")
        await unfreeze_account.finish(msg)
            
    except Exception as e:
        logger.error(f"Error in unfreeze_account: {e}")
        await unfreeze_account.finish(f"解冻账号失败：{str(e)}")
