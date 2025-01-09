from datetime import datetime
from nonebot import on_command, get_bot  # 添加 get_bot 导入
from nonebot.adapters.telegram import Bot, Message, Event
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from nonebot.log import logger

from ..database.database_manager import AccountManager
from ..config import SERVER_TYPES, DEFAULT_DAYS

# 注册命令
bind_account = on_command("bind", aliases={"绑定游戏账号"}, priority=5, block=True)
delete_account = on_command("unbind", aliases={"删除游戏账号"}, priority=5, block=True)
list_accounts = on_command("accounts", aliases={"查看账号列表"}, priority=5, block=True)
modify_account = on_command("modify", aliases={"修改账号信息", "修改账号"}, priority=5, block=True)
admin_delete = on_command("force_delete", aliases={"强制删除账号"}, permission=SUPERUSER, priority=5, block=True)
admin_search = on_command("search", aliases={"搜索账号"}, permission=SUPERUSER, priority=5, block=True)

@bind_account.handle()
async def handle_bind(event: MessageEvent, args: Message = CommandArg()):
    """处理账号绑定命令"""
    user_id = str(event.get_user_id())
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await bind_account.finish("请提供账号信息！\n格式：/绑定游戏账号 账号 密码 服务器(官服/b服)")
            return

        args_list = args_text.split()
        if len(args_list) != 3:
            await bind_account.finish("参数格式错误！\n格式：/绑定游戏账号 账号 密码 服务器(官服/b服)")
            return
            
        username, password, server = args_list
        
        if server not in SERVER_TYPES:
            await bind_account.finish("服务器类型错误！只支持：官服/b服")
            return
            
        server_type = SERVER_TYPES[server]
        
        # 检查账号是否已存在
        existing_account = AccountManager.check_account_exists(username, server_type)
        if existing_account:
            await bind_account.finish(
                f"该账号已被绑定！\n"
                f"账号: {username}\n"
                f"服务器: {server}\n"
                f"绑定用户: {existing_account.user_id}"
            )
            return
            
        # 创建新账号
        account, config = AccountManager.create_account(
            user_id=user_id,
            username=username,
            password=password,
            server=server_type,
            default_days=DEFAULT_DAYS
        )
        
        msg = f"""账号绑定成功！
账号：`{username}`
序号：`{account.account_index}`
服务器：`{server}`
用户ID：`{user_id}`
剩余天数：`{account.left_days}`天

已创建默认配置：
- 作战关卡：`{config.fight_stages}`
- 理智药使用上限：`{config.max_drug_times}`
- 源石使用上限：`{config.max_stone_times}`
- 自动任务：已全部开启
- 商店优先级：已设置默认值

请注意：
0.先绑定设备序号，并且保证你的设备adb能正常调用
1. 账号有效期为{account.left_days}天
2. 剩余2天时会收到提醒
3. 过期后账号将被冻结
4. 请记住账号序号：{account.account_index}
5. 可使用 /账号设置 命令修改配置"""

        logger.info(f"User {user_id} bound new account {username} with default config")
        await bind_account.finish(msg, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error in bind_account: {e}")
        await bind_account.finish(f"绑定结果：{str(e)}")



@delete_account.handle()
async def handle_delete(event: MessageEvent, args: Message = CommandArg()):
    """处理账号删除命令"""
    user_id = str(event.get_user_id())
    # 修改：通过 get_bot() 获取 bot 实例
    bot = get_bot()
    is_admin = str(user_id) in bot.config.superusers
    
    try:
        target_id = args.extract_plain_text().strip()
        if not target_id:
            await delete_account.finish("请提供要删除的账号信息！\n" + 
                                    ("管理员格式：/删除游戏账号 账号ID\n" if is_admin else "格式：/unbind 账号序号"))
            return
            
        try:
            account_index = int(target_id)
        except ValueError:
            await delete_account.finish("账号序号必须是数字！")
            return
            
        account, msg = AccountManager.delete_account(user_id, account_index, is_admin)
        
        if not account:
            await delete_account.finish(msg)
            return
            
        server = "官服" if account.server == "official" else "B服"
        msg = f"""账号删除成功！
数据库ID：`{account.id}`
账号序号：`{account_index}`
用户名：`{account.username}`
服务器：`{server}`
用户ID：`{account.user_id}`"""

        if is_admin and account.user_id != user_id:
            msg += f"\n[管理员操作] 操作者：`{user_id}`"

        logger.info(f"User {user_id} deleted account {account.username}")
        await delete_account.finish(msg, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error in delete_account: {e}")
        await delete_account.finish(f"删除结果：{str(e)}")

@list_accounts.handle()
async def handle_list(event: MessageEvent):
    """处理查看账号列表命令"""
    user_id = str(event.get_user_id())
    # 修改：通过 get_bot() 获取 bot 实例
    bot = get_bot()
    is_admin = str(user_id) in bot.config.superusers
    
    try:
        accounts = AccountManager.list_accounts(user_id, is_admin)
        
        if not accounts:
            await list_accounts.finish("没有找到任何账号！")
            return
            
        if is_admin:
            msg = "所有账号列表：\n"
            for account in accounts:
                msg += f"""ID：`{account.id}`
用户ID：`{account.user_id}`
账号：`{account.username}`
剩余天数：`{account.left_days}`天
---------------\n"""
        else:
            msg = "账号列表：\n"
            for account in accounts:
                server_name = "官服" if account.server == "official" else "B服"
                status = " [已冻结]" if account.is_frozen else ""
                device_info = f" - 设备{account.device}" if account.device else ""
                time_info = f" - 剩余{account.left_days}天"
                
                msg += f"`{account.account_index}`. `{account.username}` (`{server_name}`){device_info}{time_info}{status}\n"
            
        await list_accounts.finish(msg.strip(), parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error in list_accounts: {e}")
        await list_accounts.finish(f"获取账号列表失败：{str(e)}")

@modify_account.handle()
async def handle_modify_account(event: MessageEvent, args: Message = CommandArg()):
    """处理修改账号信息命令"""
    user_id = str(event.get_user_id())
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await modify_account.finish(
                "请提供修改信息！\n"
                "格式：/修改账号信息 账号序号 新账号名 新密码 服务器(官服/b服)\n"
                "注意：如果不需要修改某项，请用'-'代替"
            )
            return

        args_list = args_text.split()
        if len(args_list) != 4:
            await modify_account.finish(
                "参数格式错误！\n"
                "格式：/修改账号信息 账号序号 新账号名 新密码 服务器(官服/b服)\n"
                "注意：如果不需要修改某项，请用'-'代替"
            )
            return
            
        try:
            account_index = int(args_list[0])
        except ValueError:
            await modify_account.finish("账号序号必须是数字！")
            return
            
        new_username = None if args_list[1] == "-" else args_list[1]
        new_password = None if args_list[2] == "-" else args_list[2]
        new_server = None if args_list[3] == "-" else SERVER_TYPES.get(args_list[3])
        
        if args_list[3] != "-" and args_list[3] not in SERVER_TYPES:
            await modify_account.finish("服务器类型错误！只支持：官服/b服")
            return
            
        account, msg = AccountManager.modify_account(
            user_id=user_id,
            account_index=account_index,
            new_username=new_username,
            new_password=new_password,
            new_server=new_server
        )
        
        if not account:
            await modify_account.finish(msg)
            return
            
        changes = []
        if new_username:
            changes.append(f"账号: `{account.username}`")
        if new_password:
            changes.append(f"密码: `{new_password}`")
        if new_server:
            server_name = "官服" if new_server == "official" else "B服"
            changes.append(f"服务器: `{server_name}`")
        
        msg = f"""账号信息修改成功！
账号序号：`{account_index}`
修改项：
""" + "\n".join(changes)

        logger.info(f"User {user_id} modified account {account.username} info")
        await modify_account.finish(msg, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error in modify_account: {e}")
        await modify_account.finish(f"修改账号信息失败：{str(e)}")

@admin_search.handle()
async def handle_admin_search(event: MessageEvent, args: Message = CommandArg()):
    """管理员通过用户ID搜索账号"""
    try:
        user_id = args.extract_plain_text().strip()
        if not user_id:
            await admin_search.finish("请提供要查询的用户ID！\n格式：/搜索账号 用户ID")
            return

        accounts = AccountManager.search_accounts(user_id)

        if not accounts:
            await admin_search.finish(f"未找到用户ID：{user_id}的绑定账号！")
            return

        msg = f"用户ID：`{user_id}` 的绑定账号信息：\n"
        msg += "="*30 + "\n"

        for account in accounts:
            server_name = "官服" if account.server == "official" else "B服"
            status = " [已冻结]" if account.is_frozen else ""
            freeze_info = f"\n冻结原因：{account.freeze_reason}" if account.is_frozen else ""
            
            msg += f"""ID：`{account.id}`
账号序号：`{account.account_index}`
账号：`{account.username}`
服务器：`{server_name}`
剩余天数：`{account.left_days}`天{status}{freeze_info}
---------------\n"""

        await admin_search.finish(msg.strip(), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in admin_search: {e}")
        await admin_search.finish(f"搜索失败：{str(e)}")
