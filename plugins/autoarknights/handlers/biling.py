# biling.py
from nonebot import require, get_bot, get_driver
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from nonebot import on_command
import asyncio

from ..database.database_manager import BillingManager

# 注册命令
admin_renew = on_command("续期账号", aliases={"addtime"}, permission=SUPERUSER, priority=5, block=True)
check_time = on_command("查看时间", aliases={"checktime"}, priority=5, block=True)

async def check_accounts_time():
    """检查账号剩余时间并处理"""
    try:
        # 使用BillingManager检查账号时间
        expired_accounts, warning_accounts = await BillingManager.check_accounts_time()
        
        # 通知用户
        bot = get_bot()
        
        # 发送过期通知
        for account in expired_accounts:
            try:
                msg = f"""您的账号已过期并被冻结！
账号：{account.username}
序号：{account.account_index}
服务器：{'官服' if account.server == 'official' else 'B服'}
剩余天数：0
请联系管理员续期解冻。"""
                await bot.send_private_msg(user_id=int(account.qq), message=msg)
            except Exception as e:
                logger.error(f"Failed to notify user {account.qq} about expiry: {e}")
        
        # 发送即将过期警告
        for account in warning_accounts:
            try:
                msg = f"""您的账号即将过期！
账号：{account.username}
序号：{account.account_index}
服务器：{'官服' if account.server == 'official' else 'B服'}
剩余天数：{account.left_days}
请及时联系管理员续期。"""
                await bot.send_private_msg(user_id=int(account.qq), message=msg)
            except Exception as e:
                logger.error(f"Failed to notify user {account.qq} about warning: {e}")
                    
    except Exception as e:
        logger.error(f"Error in check_accounts_time: {e}")

# 注册定时任务，每天0点执行
scheduler = require("nonebot_plugin_apscheduler").scheduler

@scheduler.scheduled_job("cron", hour="0", minute="0")
async def check_time_task():
    """每天0点检查账号时间"""
    await check_accounts_time()

@admin_renew.handle()
async def handle_renew(event: MessageEvent, args: Message = CommandArg()):
    """管理员续期账号"""
    admin_qq = str(event.get_user_id())
    
    try:
        args_list = args.extract_plain_text().split()
        if len(args_list) != 3:
            await admin_renew.send(
                "格式：续期账号 QQ号 账号序号 续期天数\n"
                "示例：续期账号 123456 1 32\n"
                "说明：可提前续期，天数将累加"
            )
            return
            
        target_qq, account_index, add_days = args_list
        
        try:
            account_index = int(account_index)
            add_days = int(add_days)
        except ValueError:
            await admin_renew.send("账号序号和续期天数必须是数字！")
            return
            
        if add_days <= 0:
            await admin_renew.send("续期天数必须大于0！")
            return
            
        # 使用BillingManager续期账号
        account, message = BillingManager.renew_account(target_qq, account_index, add_days)
        if not account:
            await admin_renew.send(message)
            return
        
        msg = f"""账号续期成功！
账号：{account.username}
序号：{account_index}
所属QQ：{target_qq}
服务器：{'官服' if account.server == 'official' else 'B服'}
原剩余天数：{account.left_days - add_days}天
续期天数：{add_days}天
新剩余天数：{account.left_days}天
状态：{'已解冻' if not account.is_frozen else '已冻结'}
操作管理员：{admin_qq}"""
        
        logger.info(f"Admin {admin_qq} renewed account {account.username} for user {target_qq} with {add_days} days")
        await admin_renew.send(msg)
        
        # 通知用户
        try:
            bot = get_bot()
            user_msg = f"""您的账号已续期！
账号：{account.username}
序号：{account_index}
服务器：{'官服' if account.server == 'official' else 'B服'}
原剩余天数：{account.left_days - add_days}天
续期天数：{add_days}天
新剩余天数：{account.left_days}天
状态：{'已解冻' if not account.is_frozen else '已冻结'}"""
            await bot.send_private_msg(user_id=int(target_qq), message=user_msg)
        except Exception as e:
            logger.error(f"Failed to notify user {target_qq}: {e}")
            
    except Exception as e:
        logger.error(f"Error in admin_renew: {e}")
        await admin_renew.send(f"续期账号失败：{str(e)}")

@check_time.handle()
async def handle_check_time(event: MessageEvent, args: Message = CommandArg()):
    """查询账号剩余时间"""
    qq_id = str(event.get_user_id())
    
    try:
        account_index = args.extract_plain_text().strip()
        
        if account_index:
            try:
                account_index = int(account_index)
            except ValueError:
                await check_time.send("账号序号必须是数字！")
                return

        # 使用BillingManager获取账号时间信息
        accounts = BillingManager.get_account_time(qq_id, account_index if account_index else None)
        
        if not accounts:
            await check_time.send("未找到账号信息！")
            return
            
        if account_index:
            # 显示单个账号信息
            account = accounts[0]
            msg = f"""账号时间信息：
序号：{account.account_index}
用户名：{account.username}
服务器：{'官服' if account.server == 'official' else 'B服'}
剩余天数：{account.left_days}天
状态：{'已冻结' if account.is_frozen else '正常'}"""
        else:
            # 显示所有账号信息
            msg = "账号时间信息：\n"
            for account in accounts:
                server_name = "官服" if account.server == "official" else "B服"
                status = " [已冻结]" if account.is_frozen else ""
                msg += f"{account.account_index}. {account.username} ({server_name}) - 剩余 {account.left_days} 天{status}\n"
        
        await check_time.send(msg.strip())
            
    except Exception as e:
        logger.error(f"Error in check_time: {e}")
        await check_time.send(f"查询时间失败：{str(e)}")