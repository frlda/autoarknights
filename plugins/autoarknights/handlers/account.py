from datetime import datetime
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from nonebot.log import logger
from sqlmodel import select
from nonebot import get_bot

from plugins.autoarknights.database.models import ArkConfig

from ..database import ArkAccount, get_session
from ..config import SERVER_TYPES,DEFAULT_DAYS

# 注册命令
bind_account = on_command("绑定游戏账号", aliases={"bind"}, priority=5, block=True)
delete_account = on_command("删除游戏账号", aliases={"unbind"}, priority=5, block=True)
list_accounts = on_command("查看账号列表", aliases={"accounts"}, priority=5, block=True)
modify_account = on_command("修改账号信息", aliases={"修改账号"}, priority=5, block=True)
admin_delete = on_command("强制删除账号", permission=SUPERUSER, priority=5, block=True)
admin_search = on_command("搜索账号", permission=SUPERUSER, priority=5, block=True)

@bind_account.handle()
async def handle_bind(event: MessageEvent, args: Message = CommandArg()):
    """处理账号绑定命令"""
    qq_id = str(event.get_user_id())
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await bind_account.send("请提供账号信息！\n格式：绑定游戏账号 账号 密码 服务器(官服/b服)")
            return

        args_list = args_text.split()
        if len(args_list) != 3:
            await bind_account.send("参数格式错误！\n格式：绑定游戏账号 账号 密码 服务器(官服/b服)")
            return
            
        username, password, server = args_list
        
        if server not in SERVER_TYPES:
            await bind_account.send("服务器类型错误！只支持：官服/b服")
            return
            
        server_type = SERVER_TYPES[server]
            
        with get_session() as session:
            # 检查该QQ下已有账号数量
            stmt = select(ArkAccount).where(ArkAccount.qq == qq_id)
            existing_accounts = session.exec(stmt).all()
            account_index = len(existing_accounts) + 1
            
            # 检查是否已绑定该账号
            stmt = select(ArkAccount).where(
                ArkAccount.username == username,
                ArkAccount.server == server_type
            )
            existing_account = session.exec(stmt).first()
            if existing_account:
                await bind_account.send(
                    f"该账号已被绑定！\n"
                    f"账号：{username}\n"
                    f"服务器：{server}\n"
                    f"绑定QQ：{existing_account.qq}"
                )
                return
            
            # 创建新账号
            new_account = ArkAccount(
                qq=qq_id,
                username=username,
                password=password,
                server=server_type,
                account_index=account_index,
                left_days=DEFAULT_DAYS
            )
            
            # 创建默认配置
            new_config = ArkConfig(
                username=username,
                # 默认作战配置
                fight_stages="jm hd ce ls pr ap",
                max_drug_times=0,
                max_stone_times=0,
                
                # 默认自动招募配置
                auto_recruit_config={
                    "auto_recruit0": True,
                    "auto_recruit1": True,
                    "auto_recruit4": True,
                    "auto_recruit5": True,
                    "auto_recruit6": False
                },
                
                # 默认商店配置
                shop_config={
                    "high_priority": "聘 土 装置 技",
                    "low_priority": "碳 家 急"
                },
                
                # 默认任务配置
                task_config={
                    "collect_mail": True,
                    "battle_loop": True,
                    "auto_recruit": True,
                    "visit_friends": True,
                    "base_collect": True,
                    "base_shift": True,
                    "manufacture_boost": True,
                    "clue_exchange": True,
                    "deputy_change": True,
                    "credit_shop": True,
                    "public_recruit": True,
                    "mission_collect": True,
                    "time_limited": True,
                    "shop_purchase": True,
                    "story_unlock": True,
                    "skland_checkin": True
                },
                
                # 其他默认配置
                inherit_settings=False
            )
            
            try:
                session.add(new_account)
                session.add(new_config)
                session.commit()
                session.refresh(new_account)
                session.refresh(new_config)
                
                msg = f"""账号绑定成功！
账号：{username}
序号：{account_index}
服务器：{server}
QQ号码：{qq_id}
剩余天数：{new_account.left_days}天

已创建默认配置：
- 作战关卡：{new_config.fight_stages}
- 理智药使用上限：{new_config.max_drug_times}
- 源石使用上限：{new_config.max_stone_times}
- 自动任务：已全部开启
- 商店优先级：已设置默认值

请注意：
1. 账号有效期为{new_account.left_days}天
2. 剩余2天时会收到提醒
3. 过期后账号将被冻结
4. 请记住账号序号：{account_index}
5. 可使用"账号设置"命令修改配置"""
                
                logger.info(f"User {qq_id} bound new account {username} with default config")
                await bind_account.send(msg)
                
            except Exception as e:
                logger.error(f"Database error while binding account: {e}")
                await bind_account.send("数据库操作失败，请稍后重试。")
            
    except Exception as e:
        logger.error(f"Error in bind_account: {e}")
        await bind_account.send(f"绑定失败：{str(e)}")

        
@delete_account.handle()
async def handle_delete(event: MessageEvent, args: Message = CommandArg()):
    """处理账号删除命令"""
    qq_id = str(event.get_user_id())
    bot = get_bot()
    is_admin = str(qq_id) in bot.config.superusers
    
    try:
        target_id = args.extract_plain_text().strip()
        if not target_id:
            await delete_account.send("请提供要删除的账号信息！\n" + 
                                    ("管理员格式：删除游戏账号 账号ID\n" if is_admin else "格式：删除游戏账号 账号序号"))
            return
            
        with get_session() as session:
            if is_admin:
                try:
                    account_id = int(target_id)
                    stmt = select(ArkAccount).where(ArkAccount.id == account_id)
                except ValueError:
                    await delete_account.send("账号ID必须是数字！")
                    return
            else:
                try:
                    account_index = int(target_id)
                    stmt = select(ArkAccount).where(
                        ArkAccount.qq == qq_id,
                        ArkAccount.account_index == account_index
                    )
                except ValueError:
                    await delete_account.send("账号序号必须是数字！")
                    return

            account = session.exec(stmt).first()
            
            if not account:
                await delete_account.send(f"未找到指定的账号！")
                return

            if not is_admin and account.qq != qq_id:
                await delete_account.send("您没有权限删除该账号！")
                return

            # 同时删除账号配置
            config_stmt = select(ArkConfig).where(ArkConfig.username == account.username)
            config = session.exec(config_stmt).first()
            if config:
                session.delete(config)
                
            username = account.username
            server = "官服" if account.server == "official" else "B服"
            owner_qq = account.qq
            acc_index = account.account_index
            
            session.delete(account)
            
            # 更新该QQ用户其他账号的序号
            stmt = select(ArkAccount).where(
                ArkAccount.qq == owner_qq,
                ArkAccount.account_index > acc_index
            ).order_by("account_index")
            
            for acc in session.exec(stmt):
                acc.account_index -= 1
                
            session.commit()
            
            msg = f"""账号删除成功！
数据库ID：{account.id}
账号序号：{acc_index}
用户名：{username}
服务器：{server}
所属QQ：{owner_qq}
配置信息：{'已清除' if config else '无需清除'}"""

            if is_admin and owner_qq != qq_id:
                msg += f"\n[管理员操作] 操作者：{qq_id}"

            logger.info(f"User {qq_id} deleted account {username} (owner: {owner_qq}) and its config")
            await delete_account.send(msg)
            
    except Exception as e:
        logger.error(f"Error in delete_account: {e}")
        await delete_account.send(f"删除失败：{str(e)}")

@list_accounts.handle()
async def handle_list(event: MessageEvent):
    """处理查看账号列表命令"""
    qq_id = str(event.get_user_id())
    # 检查是否为管理员
    bot = get_bot()
    is_admin = str(qq_id) in bot.config.superusers
    
    try:
        with get_session() as session:
            if is_admin:
                # 管理员查看所有账号
                stmt = select(ArkAccount).order_by("qq", "account_index")
                accounts = session.exec(stmt).all()
                
                if not accounts:
                    await list_accounts.send("目前没有任何绑定的账号！")
                    return
                
                msg = "所有账号列表：\n"
                for account in accounts:
                    msg += f"""ID：{account.id}
QQ：{account.qq}
账号：{account.username}
剩余天数：{account.left_days}天
---------------\n"""
            
            else:
                # 普通用户只能查看自己的账号
                stmt = select(ArkAccount).where(
                    ArkAccount.qq == qq_id
                ).order_by("account_index")
                accounts = session.exec(stmt).all()
                
                if not accounts:
                    await list_accounts.send("你还没有绑定任何账号！")
                    return

                msg = "账号列表：\n"
                for account in accounts:
                    server_name = "官服" if account.server == "official" else "B服"
                    status = " [已冻结]" if account.is_frozen else ""
                    device_info = f" - 设备{account.device}" if account.device else ""
                    time_info = f" - 剩余{account.left_days}天"
                    
                    msg += f"{account.account_index}. {account.username} ({server_name}){device_info}{time_info}{status}\n"
                
            await list_accounts.send(msg.strip())
            
    except Exception as e:
        logger.error(f"Error in list_accounts: {e}")
        await list_accounts.send(f"获取账号列表失败：{str(e)}")

@modify_account.handle()
async def handle_modify_account(event: MessageEvent, args: Message = CommandArg()):
    """处理修改账号信息命令"""
    qq_id = str(event.get_user_id())
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await modify_account.send(
                "请提供修改信息！\n"
                "格式：修改账号信息 账号序号 新账号名 新密码 服务器(官服/b服)\n"
                "注意：如果不需要修改某项，请用'-'代替"
            )
            return

        args_list = args_text.split()
        if len(args_list) != 4:
            await modify_account.send(
                "参数格式错误！\n"
                "格式：修改账号信息 账号序号 新账号名 新密码 服务器(官服/b服)\n"
                "注意：如果不需要修改某项，请用'-'代替\n"
                "例如：修改账号信息 1 new_account - 官服  (只修改账号名和服务器)\n"
                "例如：修改账号信息 1 - new_password -  (只修改密码)"
            )
            return
            
        try:
            account_index = int(args_list[0])
        except ValueError:
            await modify_account.send("账号序号必须是数字！")
            return
            
        new_username = args_list[1]
        new_password = args_list[2]
        new_server = args_list[3]
            
        with get_session() as session:
            # 查找对应账号
            stmt = select(ArkAccount).where(
                ArkAccount.qq == qq_id,
                ArkAccount.account_index == account_index
            )
            account = session.exec(stmt).first()
            
            if not account:
                await modify_account.send(f"未找到序号为 {account_index} 的账号！")
                return
            
            # 保存旧信息用于显示
            old_username = account.username
            old_password = account.password
            old_server = "官服" if account.server == "official" else "B服"
            
            # 检查新账号名是否已被绑定（如果要修改账号名）
            if new_username != "-":
                stmt = select(ArkAccount).where(
                    ArkAccount.username == new_username,
                    ArkAccount.server == (
                        SERVER_TYPES.get(new_server) if new_server != "-" 
                        else account.server
                    )
                )
                existing_account = session.exec(stmt).first()
                if existing_account and existing_account.id != account.id:
                    await modify_account.send(
                        f"账号名 {new_username} 已被其他用户绑定！\n"
                        f"绑定QQ：{existing_account.qq}"
                    )
                    return
            
            # 更新信息
            if new_username != "-":
                account.username = new_username
            if new_password != "-":
                account.password = new_password
            if new_server != "-":
                if new_server not in SERVER_TYPES:
                    await modify_account.send("服务器类型错误！只支持：官服/b服")
                    return
                account.server = SERVER_TYPES[new_server]
            
            session.add(account)
            session.commit()
            
            # 构建修改信息提示
            changes = []
            if new_username != "-":
                changes.append(f"账号: {old_username} -> {new_username}")
            if new_password != "-":
                changes.append(f"密码: {old_password} -> {new_password}")
            if new_server != "-":
                new_server_name = "官服" if account.server == "official" else "B服"
                changes.append(f"服务器: {old_server} -> {new_server_name}")
            
            msg = f"""账号信息修改成功！
账号序号：{account_index}
修改项：
""" + "\n".join(changes)

            logger.info(f"User {qq_id} modified account {old_username} info")
            await modify_account.send(msg)
            
    except Exception as e:
        logger.error(f"Error in modify_account: {e}")
        await modify_account.send(f"修改账号信息失败：{str(e)}")
                


@admin_delete.handle()
async def handle_admin_delete(event: MessageEvent, args: Message = CommandArg()):
    """管理员强制删除账号"""
    qq_id = str(event.get_user_id())
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await admin_delete.send("请提供删除信息！\n格式：强制删除账号 QQ号 账号序号")
            return

        args_list = args_text.split()
        if len(args_list) != 2:
            await admin_delete.send("参数格式错误！\n格式：强制删除账号 QQ号 账号序号")
            return
            
        try:
            target_qq = str(args_list[0])
            account_index = int(args_list[1])
        except ValueError:
            await admin_delete.send("账号序号必须是数字！")
            return
            
        with get_session() as session:
            # 查找对应账号
            stmt = select(ArkAccount).where(
                ArkAccount.qq == target_qq,
                ArkAccount.account_index == account_index
            )
            account = session.exec(stmt).first()
            
            if not account:
                await admin_delete.send(f"未找到该用户的序号为 {account_index} 的账号！")
                return
                
            username = account.username
            server = "官服" if account.server == "official" else "B服"
            
            # 删除账号
            session.delete(account)
            
            # 更新该QQ用户其他账号的序号
            stmt = select(ArkAccount).where(
                ArkAccount.qq == target_qq,
                ArkAccount.account_index > account_index
            ).order_by("account_index")
            
            for acc in session.exec(stmt):
                acc.account_index -= 1
                
            session.commit()
            
            msg = f"""管理员强制删除账号成功！
数据库ID：{account.id}
账号序号：{account_index}
用户名：{username}
服务器：{server}
所属QQ：{target_qq}
操作者：{qq_id}"""

            logger.info(f"Admin {qq_id} force deleted account {username} (owner: {target_qq})")
            await admin_delete.send(msg)
            
    except Exception as e:
        logger.error(f"Error in admin_delete: {e}")
        await admin_delete.send(f"删除失败：{str(e)}")




@admin_search.handle()
async def handle_admin_search(event: MessageEvent, args: Message = CommandArg()):
    """管理员通过QQ号搜索账号"""
    try:
        qq_number = args.extract_plain_text().strip()
        if not qq_number:
            await admin_search.send("请提供要查询的QQ号！\n格式：搜索账号 QQ号")
            return

        # 验证输入是否为有效的QQ号
        if not qq_number.isdigit():
            await admin_search.send("请输入有效的QQ号！")
            return

        with get_session() as session:
            # 查询指定QQ号的所有账号
            stmt = select(ArkAccount).where(ArkAccount.qq == qq_number).order_by("account_index")
            accounts = session.exec(stmt).all()

            if not accounts:
                await admin_search.send(f"未找到QQ号：{qq_number}的绑定账号！")
                return

            msg = f"QQ：{qq_number} 的绑定账号信息：\n"
            msg += "="*30 + "\n"

            for account in accounts:
                server_name = "官服" if account.server == "official" else "B服"
                status = " [已冻结]" if account.is_frozen else ""
                freeze_info = f"\n冻结原因：{account.freeze_reason}" if account.is_frozen else ""
                
                msg += f"""ID：{account.id}
账号序号：{account.account_index}
账号：{account.username}
服务器：{server_name}
剩余天数：{account.left_days}天{status}{freeze_info}
---------------\n"""

            await admin_search.send(msg.strip())

    except Exception as e:
        logger.error(f"Error in admin_search: {e}")
        await admin_search.send(f"搜索失败：{str(e)}")