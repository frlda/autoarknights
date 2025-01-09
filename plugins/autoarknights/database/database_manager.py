from datetime import datetime
from typing import List, Optional, Tuple, Dict
from sqlmodel import Session, select, delete
from .models import ArkAccount, ArkConfig
from ..database import engine
from ..config import MIN_DEVICE, MAX_DEVICE, WARNING_DAYS, device_limits

def get_session():
    return Session(engine)

class AccountManager:
    @staticmethod
    def check_account_exists(username: str, server: str) -> Optional[ArkAccount]:
        """检查账号是否已存在"""
        with Session(engine) as session:
            stmt = select(ArkAccount).where(
                ArkAccount.username == username,
                ArkAccount.server == server
            )
            return session.exec(stmt).first()

    @staticmethod
    def create_account(
        user_id: str,
        username: str,
        password: str,
        server: str,
        default_days: int = 30,
        account_index: Optional[int] = None
    ) -> Tuple[ArkAccount, ArkConfig]:
        """创建新账号"""
        with Session(engine) as session:
            # 检查账号是否已存在
            existing = AccountManager.check_account_exists(username, server)
            if existing:
                raise Exception(f"该账号已被绑定！\n账号:{username}\n服务器:{server}\n绑定用户:{existing.user_id}")

            # 如果没有指定 account_index，自动生成
            if account_index is None:
                stmt = select(ArkAccount).where(ArkAccount.user_id == user_id)
                user_accounts = session.exec(stmt).all()
                account_index = len(user_accounts) + 1
            
            # 创建新账号
            new_account = ArkAccount(
                user_id=user_id,
                username=username,
                password=password,
                server=server,
                account_index=account_index,
                left_days=default_days,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(new_account)
            session.flush()  # 确保 new_account.id 可用
            
            # 创建默认配置
            default_config = ArkConfig(
                username=username,  # 添加用户名关联
                fight_stages="jm hd ce ls pr ap",  # 从models中的默认值
                max_drug_times=0,  # 默认不使用理智药
                max_stone_times=0,  # 默认不使用源石
                auto_recruit_config={  # 从models中的默认值
                    "auto_recruit0": True,
                    "auto_recruit1": True,
                    "auto_recruit4": True,
                    "auto_recruit5": True,
                    "auto_recruit6": False
                },
                shop_config={  # 从models中的默认值
                    "high_priority": "聘 土 装置 技",
                    "low_priority": "碳 家 急"
                },
                task_config={  # 从models中的默认值
                    "collect_mail": True,      # 邮件收取
                    "battle_loop": True,       # 轮次作战
                    "auto_recruit": True,      # 自动招募
                    "visit_friends": True,     # 访问好友
                    "base_collect": True,      # 基建收获
                    "base_shift": True,        # 基建换班
                    "manufacture_boost": True,  # 制造加速
                    "clue_exchange": True,     # 线索交流
                    "deputy_change": True,     # 副手换人
                    "credit_shop": True,       # 信用购买
                    "public_recruit": True,    # 公开招募
                    "mission_collect": True,   # 任务收集
                    "time_limited": True,      # 限时活动
                    "shop_purchase": True,     # 商店搬空
                    "story_unlock": True,      # 故事解锁
                    "skland_checkin": True     # 森空岛签到
                },
                inherit_settings=False,  # 从models中的默认值
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(default_config)
            
            try:
                session.commit()
                session.refresh(new_account)
                session.refresh(default_config)
                return new_account, default_config
            except Exception as e:
                session.rollback()
                raise Exception(f"创建账号失败：{str(e)}")

    @staticmethod
    def delete_account(user_id: str, account_index: int, is_admin: bool = False) -> Tuple[Optional[ArkAccount], str]:
        """删除账号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id,
                ArkAccount.account_index == account_index
            )
            account = session.exec(stmt).first()
            
            if not account:
                return None, "未找到指定账号"

            # 同时删除账号配置
            config_stmt = select(ArkConfig).where(ArkConfig.username == account.username)
            config = session.exec(config_stmt).first()
            if config:
                session.delete(config)
                
            session.delete(account)
            
            # 更新该用户其他账号的序号
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id,
                ArkAccount.account_index > account_index
            ).order_by("account_index")
            
            for acc in session.exec(stmt):
                acc.account_index -= 1
                
            session.commit()
            return account, "删除成功"

    @staticmethod
    def list_accounts(user_id: str, is_admin: bool = False) -> List[ArkAccount]:
        """获取账号列表"""
        with get_session() as session:
            if is_admin:
                stmt = select(ArkAccount).order_by("user_id", "account_index")
            else:
                stmt = select(ArkAccount).where(
                    ArkAccount.user_id == user_id
                ).order_by("account_index")
            return list(session.exec(stmt).all())

    @staticmethod
    def modify_account(
        user_id: str,
        account_index: int,
        new_username: Optional[str] = None,
        new_password: Optional[str] = None,
        new_server: Optional[str] = None
    ) -> Tuple[Optional[ArkAccount], str]:
        """修改账号信息"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id,
                ArkAccount.account_index == account_index
            )
            account = session.exec(stmt).first()
            
            if not account:
                return None, "未找到指定账号"
            
            if new_username:
                account.username = new_username
            if new_password:
                account.password = new_password
            if new_server:
                account.server = new_server
            
            account.updated_at = datetime.now()
            session.add(account)
            session.commit()
            session.refresh(account)
            return account, "修改成功"

    @staticmethod
    def search_accounts(user_id: str) -> List[ArkAccount]:
        """管理员搜索指定用户的账号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id
            ).order_by("account_index")
            return list(session.exec(stmt).all())


class DeviceManager:
    @staticmethod
    def get_device_usage(session: Session) -> Dict[int, List[ArkAccount]]:
        """获取所有设备的使用情况"""
        device_usage = {i: [] for i in range(MIN_DEVICE, MAX_DEVICE + 1)}
        stmt = select(ArkAccount).where(ArkAccount.device != None)
        accounts = session.exec(stmt).all()
        
        for account in accounts:
            if account.device is not None:
                device_usage[account.device].append(account)
                
        return device_usage

    @staticmethod
    def set_device(
        user_id: str, 
        account_index: int, 
        device_id: int
    ) -> Tuple[Optional[ArkAccount], str]:
        """设置账号的设备号"""
        with get_session() as session:
            # 检查设备号是否有效
            if device_id < MIN_DEVICE or device_id > MAX_DEVICE:
                return None, f"无效的设备号！设备号范围：{MIN_DEVICE}-{MAX_DEVICE}"

            # 查找账号
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id,
                ArkAccount.account_index == account_index
            )
            account = session.exec(stmt).first()
            
            if not account:
                return None, "未找到指定账号"
            
            # 检查设备使用情况
            device_usage = DeviceManager.get_device_usage(session)
            current_usage = len(device_usage[device_id])
            device_limit = device_limits[device_id]
            
            if current_usage >= device_limit:
                return None, f"设备 {device_id} 已达到使用上限 ({current_usage}/{device_limit})"
            
            # 更新设备号
            account.device = device_id
            account.updated_at = datetime.now()
            session.add(account)
            
            try:
                session.commit()
                session.refresh(account)
                return account, "设置成功"
            except Exception as e:
                session.rollback()
                return None, f"设置设备失败：{str(e)}"

    @staticmethod
    def remove_device(
        user_id: str, 
        account_index: int
    ) -> Tuple[Optional[ArkAccount], str]:
        """移除账号的设备绑定"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id,
                ArkAccount.account_index == account_index
            )
            account = session.exec(stmt).first()
            
            if not account:
                return None, "未找到指定账号"
            
            if account.device is None:
                return None, "该账号未绑定设备"
            
            account.device = None
            account.updated_at = datetime.now()
            session.add(account)
            
            try:
                session.commit()
                session.refresh(account)
                return account, "设备解绑成功"
            except Exception as e:
                session.rollback()
                return None, f"设备解绑失败：{str(e)}"
            

class BillingManager:
    """账号计费和时间管理"""
    
    @staticmethod
    async def check_accounts_time() -> Tuple[List[ArkAccount], List[ArkAccount]]:
        """
        检查所有账号的剩余时间
        返回: (过期账号列表, 即将过期账号列表)
        """
        with get_session() as session:
            stmt = select(ArkAccount).where(ArkAccount.is_frozen == False)
            accounts: List[ArkAccount] = list(session.exec(stmt).all())
            
            expired_accounts: List[ArkAccount] = []
            warning_accounts: List[ArkAccount] = []
            
            for account in accounts:
                if account.left_days <= 0:
                    account.is_frozen = True
                    account.temp_password = account.password
                    account.password = ""
                    account.freeze_reason = "账号已过期"
                    expired_accounts.append(account)
                elif account.left_days <= WARNING_DAYS:
                    warning_accounts.append(account)
                
                account.left_days -= 1
                account.updated_at = datetime.now()
            
            session.commit()
            return expired_accounts, warning_accounts
        
    @staticmethod
    def renew_account(user_id: str, account_index: int, add_days: int) -> Tuple[Optional[ArkAccount], str]:
        """续期账号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id,
                ArkAccount.account_index == account_index
            )
            account: Optional[ArkAccount] = session.exec(stmt).first()
            
            if not account:
                return None, "未找到该账号"

            original_days = account.left_days
            account.left_days += add_days
            
            if account.is_frozen and account.temp_password:
                account.password = account.temp_password
                account.temp_password = None
                account.is_frozen = False
                account.freeze_reason = None
            
            account.updated_at = datetime.now()
            session.commit()
            session.refresh(account)
            
            return account, "续期成功"
            
    @staticmethod
    def get_account_time(user_id: str, account_index: Optional[int] = None) -> List[ArkAccount]:
        """获取账号剩余时间信息"""
        with get_session() as session:
            if account_index is not None:
                stmt = select(ArkAccount).where(
                    ArkAccount.user_id == user_id,
                    ArkAccount.account_index == account_index
                )
                result: Optional[ArkAccount] = session.exec(stmt).first()
                return [result] if result else []
            else:
                stmt = select(ArkAccount).where(
                    ArkAccount.user_id == user_id
                ).order_by("account_index")
                return list(session.exec(stmt).all())
            

class FreezeManager:
    """账号冻结管理"""
    
    @staticmethod
    def freeze_account(user_id: str, account_index: int) -> Tuple[Optional[ArkAccount], str]:
        """冻结账号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id,
                ArkAccount.account_index == account_index
            )
            account: Optional[ArkAccount] = session.exec(stmt).first()
            
            if not account:
                return None, "未找到该账号"

            if account.is_frozen:
                return None, "账号已经处于冻结状态"
                
            account.temp_password = account.password
            account.password = ""
            account.is_frozen = True
            account.updated_at = datetime.now()
            session.commit()
            session.refresh(account)
            
            return account, "冻结成功"

    @staticmethod
    def unfreeze_account(user_id: str, account_index: int) -> Tuple[Optional[ArkAccount], str]:
        """解冻账号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.user_id == user_id,
                ArkAccount.account_index == account_index
            )
            account: Optional[ArkAccount] = session.exec(stmt).first()
            
            if not account:
                return None, "未找到该账号"

            if not account.is_frozen:
                return None, "账号未处于冻结状态"
            
            if account.freeze_reason == "账号已过期":
                return None, "账号已过期，请联系管理员续期"
            
            if not account.temp_password:
                return None, "账号密码数据丢失，无法解冻"
                
            account.password = account.temp_password
            account.temp_password = None
            account.is_frozen = False
            account.updated_at = datetime.now()
            session.commit()
            session.refresh(account)
            
            return account, "解冻成功"