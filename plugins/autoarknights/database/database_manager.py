from datetime import datetime
from typing import List, Optional, Dict, Tuple, Union, Sequence
from sqlmodel import Session, select
from nonebot.log import logger

from .models import ArkAccount
from ..database import get_session
from ..config import MIN_DEVICE, MAX_DEVICE, device_limits, WARNING_DAYS, DEFAULT_DAYS

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
            
            session.commit()
            return expired_accounts, warning_accounts
        

    @staticmethod
    def renew_account(target_qq: str, account_index: int, add_days: int) -> Tuple[Optional[ArkAccount], str]:
        """续期账号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.qq == target_qq,
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
            
            session.commit()
            session.refresh(account)
            
            return account, "续期成功"
            
    @staticmethod
    def get_account_time(qq: str, account_index: Optional[int] = None) -> List[ArkAccount]:
        """获取账号剩余时间信息"""
        with get_session() as session:
            if account_index is not None:
                stmt = select(ArkAccount).where(
                    ArkAccount.qq == qq,
                    ArkAccount.account_index == account_index
                )
                result: Optional[ArkAccount] = session.exec(stmt).first()
                return [result] if result else []
            else:
                stmt = select(ArkAccount).where(
                    ArkAccount.qq == qq
                ).order_by("account_index")
                return list(session.exec(stmt).all())

class DeviceManager:
    """设备管理"""
    
    @staticmethod
    async def get_device_usage(session: Session) -> Dict[int, List[ArkAccount]]:
        """获取所有设备的使用情况"""
        stmt = select(ArkAccount).where(ArkAccount.device != None)
        accounts: List[ArkAccount] = list(session.exec(stmt).all())
        
        usage: Dict[int, List[ArkAccount]] = {i: [] for i in range(MIN_DEVICE, MAX_DEVICE + 1)}
        for account in accounts:
            if account.device in usage:
                usage[account.device].append(account)
        return usage

    @staticmethod
    async def set_device(qq: str, account_index: int, device_id: int) -> Tuple[Optional[ArkAccount], str]:
        """设置账号的设备号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.qq == qq,
                ArkAccount.account_index == account_index
            )
            account: Optional[ArkAccount] = session.exec(stmt).first()
            
            if not account:
                return None, "未找到该账号"
                
            device_usage = await DeviceManager.get_device_usage(session)
            current_usage = len(device_usage[device_id])
            device_limit = device_limits[device_id]
            
            if account.device != device_id and current_usage >= device_limit:
                return None, f"设备 {device_id} 已达到使用上限（{device_limit}个账号）"

            old_device = account.device
            account.device = device_id
            account.updated_at = datetime.now()
            session.commit()
            session.refresh(account)
            
            return account, "设置成功"

    @staticmethod
    async def set_device_limit(device_id: int, limit: int) -> Tuple[int, int, int]:
        """设置设备使用限制"""
        with get_session() as session:
            device_usage = await DeviceManager.get_device_usage(session)
            current_usage = len(device_usage[device_id])
            old_limit = device_limits[device_id]
            device_limits[device_id] = limit
            return old_limit, limit, current_usage

    @staticmethod
    def get_device_info(qq: str, account_index: Optional[int] = None) -> List[ArkAccount]:
        """获取设备信息"""
        with get_session() as session:
            if account_index is not None:
                stmt = select(ArkAccount).where(
                    ArkAccount.qq == qq,
                    ArkAccount.account_index == account_index
                )
                result: Optional[ArkAccount] = session.exec(stmt).first()
                return [result] if result else []
            else:
                stmt = select(ArkAccount).where(
                    ArkAccount.qq == qq
                ).order_by("account_index")
                return list(session.exec(stmt).all())

class FreezeManager:
    """账号冻结管理"""
    
    @staticmethod
    def freeze_account(qq: str, account_index: int) -> Tuple[Optional[ArkAccount], str]:
        """冻结账号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.qq == qq,
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
    def unfreeze_account(qq: str, account_index: int) -> Tuple[Optional[ArkAccount], str]:
        """解冻账号"""
        with get_session() as session:
            stmt = select(ArkAccount).where(
                ArkAccount.qq == qq,
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

