from datetime import datetime
from typing import Optional, Dict
from sqlmodel import Field, SQLModel, Column, JSON
from pydantic import BaseModel

class ArkAccount(SQLModel, table=True):
    __table_args__ = {'keep_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    qq: str = Field(index=True, title='QQ号')
    username: str = Field(title='游戏账号')
    password: str = Field(title='账号密码')
    server: str = Field(title='服务器类型', description='官服=official, B服=bilibili')
    device: Optional[int] = Field(default=None, title='设备号')  # 新增设备号字段
    account_index: int = Field(title='账号序号')
    created_at: datetime = Field(default_factory=datetime.now, title='创建时间')
    updated_at: datetime = Field(default_factory=datetime.now, title='更新时间')
    is_frozen: bool = Field(default=False, title='是否冻结')
    temp_password: Optional[str] = Field(default=None, title='临时保存的密码')
    left_days: int = Field(default=32, title='剩余天数')  # 新增剩余天数字段
    freeze_reason: Optional[str] = Field(default=None, title='冻结原因')

class ArkConfig(SQLModel, table=True):
    """明日方舟配置表"""
    __table_args__ = {'keep_existing': True}
    
    # 基础信息
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, title='游戏账号')  # 用于关联ArkAccount表
    
    # 作战配置
    fight_stages: str = Field(default="jm hd ce ls pr ap", title='作战关卡')
    max_drug_times: int = Field(default=0, title='理智药使用上限')
    max_stone_times: int = Field(default=0, title='源石使用上限')
    
    # 自动招募配置
    auto_recruit_config: dict = Field(
        default={
            "auto_recruit0": True,
            "auto_recruit1": True,
            "auto_recruit4": True,
            "auto_recruit5": True,
            "auto_recruit6": False
        },
        sa_column=Column(JSON)
    )
    
    # 商店配置
    shop_config: dict = Field(
        default={
            "high_priority": "聘 土 装置 技",
            "low_priority": "碳 家 急"
        },
        sa_column=Column(JSON)
    )
    
    # 任务界面配置
    task_config: dict = Field(
        default={
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
        sa_column=Column(JSON)
    )
    
    # 继承设置
    inherit_settings: bool = Field(default=False, title='是否继承设置')
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, title='创建时间')
    updated_at: datetime = Field(default_factory=datetime.now, title='更新时间')

class ArkConfigHistory(SQLModel, table=True):
    """配置修改历史表"""
    __table_args__ = {'keep_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, title='游戏账号')
    modified_at: datetime = Field(default_factory=datetime.now)
    modified_by: str = Field(title='修改人QQ')
    config_type: str = Field(title='修改类型')
    old_value: dict = Field(sa_column=Column(JSON))
    new_value: dict = Field(sa_column=Column(JSON))