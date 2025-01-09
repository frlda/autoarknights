import re
from nonebot import on_regex
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.log import logger
from sqlmodel import Session, select
from datetime import datetime
from ..database import get_session, ArkAccount, ArkConfig, ArkConfigHistory

TASK_CONFIG_ITEMS = {
    "邮件收取": "collect_mail",
    "轮次作战": "battle_loop",
    "自动招募": "auto_recruit",
    "访问好友": "visit_friends",
    "基建收获": "base_collect",
    "基建换班": "base_shift",
    "制造加速": "manufacture_boost",
    "线索交流": "clue_exchange",
    "副手换人": "deputy_change",
    "信用购买": "credit_shop",
    "公开招募": "public_recruit",
    "任务收集": "mission_collect",
    "限时活动": "time_limited",
    "商店搬空": "shop_purchase",
    "故事解锁": "story_unlock",
    "森空岛签到": "skland_checkin"
}

DIRECT_CONFIG_ITEMS = {
    "作战关卡": "fight_stages",
    "理智药使用上限": "max_drug_times",
    "源石使用上限": "max_stone_times"
}

RECRUIT_CONFIG_ITEMS = {
    "自动招募其他": "auto_recruit0",
    "自动招募车": "auto_recruit1",
    "自动招募4星": "auto_recruit4",
    "自动招募5星": "auto_recruit5",
    "自动招募6星": "auto_recruit6",
    "其他": "auto_recruit0",
    "车": "auto_recruit1",
    "4": "auto_recruit4",
    "5": "auto_recruit5",
    "6": "auto_recruit6"
}

SHOP_CONFIG_ITEMS = {
    "信用多买": "high_priority",
    "信用少买": "low_priority"
}

VALID_SHOP_ITEMS = [u"聘", u"土", u"装置", u"技", u"碳", u"家", u"急"]

ark_setting = on_regex(r"^/账号设置\s*(\d+)\s+(.+?)(?:\s+(.+))?$", priority=5)

def get_default_task_config() -> dict:
    return {
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
    }

def get_default_recruit_config() -> dict:
    return {
        "auto_recruit0": True,
        "auto_recruit1": True,
        "auto_recruit4": True,
        "auto_recruit5": True,
        "auto_recruit6": False
    }

def get_default_shop_config() -> dict:
    return {
        "high_priority": u"聘 土 装置 技",
        "low_priority": u"碳 家 急"
    }

def update_task_config(config: ArkConfig, key: str, value: bool) -> tuple[bool, bool]:
    if config.task_config is None:
        task_config = get_default_task_config()
    else:
        task_config = dict(config.task_config)
    old_value = task_config.get(key, True)
    task_config[key] = value
    config.task_config = task_config
    return old_value, value

def update_recruit_config(config: ArkConfig, key: str, value: bool) -> tuple[bool, bool]:
    if config.auto_recruit_config is None:
        recruit_config = get_default_recruit_config()
    else:
        recruit_config = dict(config.auto_recruit_config)
    old_value = recruit_config.get(key, True)
    recruit_config[key] = value
    config.auto_recruit_config = recruit_config
    return old_value, value

def validate_shop_items(items_str: str, config: ArkConfig, current_key: str) -> bool:
    items = items_str.split()
    
    if not all(item in VALID_SHOP_ITEMS for item in items):
        raise ValueError("无效的商品项，只能包含：聘、土、装置、技、碳、家、急")
    
    if len(items) != len(set(items)):
        raise ValueError("商品项不能重复")
    
    other_key = "low_priority" if current_key == "high_priority" else "high_priority"
    if config.shop_config and other_key in config.shop_config:
        other_items = config.shop_config[other_key].split()
        if any(item in other_items for item in items):
            raise ValueError("信用多买和信用少买的商品不能重复")
    
    return True

def update_shop_config(config: ArkConfig, key: str, value: str) -> tuple[str, str]:
    validate_shop_items(value, config, key)
    
    if config.shop_config is None:
        shop_config = get_default_shop_config()
    else:
        shop_config = dict(config.shop_config)
    
    old_value = shop_config.get(key, "")
    shop_config[key] = value
    config.shop_config = shop_config
    return old_value, value

@ark_setting.handle()
async def handle_setting(event: MessageEvent):
    try:
        msg = str(event.get_message()).strip()
        match = re.match(r"^/账号设置\s*(\d+)\s+(.+?)(?:\s+(.+))?$", msg)
        if not match:
            await ark_setting.finish(
                "命令格式错误！\n"
                "格式：/set <序号> <配置项> [值]\n"
                "示例：\n"
                "/set 1 作战关卡 1-7\n"
                "/set 1 邮件收取 关闭"
            )
            return

        account_index = int(match.group(1))
        config_name = match.group(2)
        value_str = match.group(3)

        if not value_str:
            await ark_setting.finish(f"请提供{config_name}的值")
            return

        with get_session() as session:
            account = session.exec(
                select(ArkAccount).where(
                    ArkAccount.user_id == str(event.get_user_id()),
                    ArkAccount.account_index == account_index
                )
            ).first()
            
            if not account:
                await ark_setting.finish(f"未找到序号为 {account_index} 的账号")
                return

            config = session.exec(
                select(ArkConfig).where(
                    ArkConfig.username == account.username
                )
            ).first()
            
            if not config:
                config = ArkConfig(username=account.username)
                session.add(config)

            try:
                old_value = None
                new_value = None
                
                if config_name in TASK_CONFIG_ITEMS:
                    value = value_str.lower() not in ['0', 'false', 'off', '关闭', '否', 'no']
                    old_value, new_value = update_task_config(
                        config, 
                        TASK_CONFIG_ITEMS[config_name],
                        value
                    )
                    display_old = "开启" if old_value else "关闭"
                    display_new = "开启" if new_value else "关闭"
                
                elif config_name in DIRECT_CONFIG_ITEMS:
                    db_key = DIRECT_CONFIG_ITEMS[config_name]
                    if config_name in ["理智药使用上限", "源石使用上限"]:
                        try:
                            value = int(value_str)
                        except ValueError:
                            await ark_setting.finish(f"无效的数值：{value_str}")
                            return
                    else:
                        value = value_str
                    
                    old_value = getattr(config, db_key, None)
                    setattr(config, db_key, value)
                    new_value = value
                    display_old = str(old_value) if old_value is not None else "未设置"
                    display_new = str(value)

                elif config_name in RECRUIT_CONFIG_ITEMS:
                    value = value_str.lower() not in ['0', 'false', 'off', '关闭', '否', 'no']
                    old_value, new_value = update_recruit_config(
                        config,
                        RECRUIT_CONFIG_ITEMS[config_name],
                        value
                    )
                    display_old = "开启" if old_value else "关闭"
                    display_new = "开启" if new_value else "关闭"

                elif config_name in SHOP_CONFIG_ITEMS:
                    try:
                        old_value, new_value = update_shop_config(
                            config,
                            SHOP_CONFIG_ITEMS[config_name],
                            value_str
                        )
                        display_old = old_value if old_value else "未设置"
                        display_new = new_value
                    except ValueError as e:
                        await ark_setting.finish(str(e))
                        return
                
                else:
                    await ark_setting.finish(f"未知的配置项：{config_name}")
                    return

                history = ArkConfigHistory(
                    username=account.username,
                    modified_by=str(event.get_user_id()),
                    config_type=config_name,
                    old_value={"value": str(old_value)},
                    new_value={"value": str(new_value)}
                )
                session.add(history)

                config.updated_at = datetime.now()
                session.commit()

                msg = (f"设置成功！\n"
                      f"账号：{account.username}\n"
                      f"序号：{account_index}\n"
                      f"配置项：{config_name}\n"
                      f"旧值：{display_old}\n"
                      f"新值：{display_new}")
                await ark_setting.send(msg)

            except Exception as e:
                session.rollback()
                logger.error(f"Database error: {e}")
                await ark_setting.finish(f"保存配置失败：{str(e)}")

    except Exception as e:
        logger.error(f"Error in handle_setting: {e}")
        await ark_setting.finish(f"设置失败：{str(e)}")
