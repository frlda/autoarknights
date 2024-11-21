from pathlib import Path
from pydantic import BaseModel, Extra
from typing import Dict, Set, Any


SERVER_TYPES: Dict[str, str] = {
    "官服": "official",
    "b服": "bilibili",
    "B服": "bilibili"
}

# 设备数量配置，请在cron/dlt.py下配置好排序和设备adb连接
MIN_DEVICE = 1
MAX_DEVICE = 9
DEFAULT_DEVICE_LIMIT = 8 
device_limits: Dict[int, int] = {i: DEFAULT_DEVICE_LIMIT for i in range(MIN_DEVICE, MAX_DEVICE + 1)}

# 定时任务配置
arknight_update_times: Set[str] = {"04:00", "12:00", "20:00"}

# 账号计费配置
WARNING_DAYS = 2  # 提醒剩余天数
DEFAULT_DAYS = 32  # 默认充值天数

# 图传配置
SCREENSHOT_CONFIG: Dict[str, Any] = {
    "enable": True,  # 是否启用图传功能
    "server_url": "http://127.0.0.1:8888",  # 图传服务器地址
    "target_groups": ["894907414"],  # 目标群组列表
    "message_template": "设备状态截图 {device} \n时间: {time}"  # 消息模板
}


class Config(BaseModel):
    # 数据库配置
    autoarknights_database_url: str = ""

    # 设备配置
    min_device: int = MIN_DEVICE
    max_device: int = MAX_DEVICE
    default_device_limit: int = DEFAULT_DEVICE_LIMIT

    class Config:
        extra = Extra.ignore

    def __init__(self, **data):
        super().__init__(**data)
        if not self.autoarknights_database_url:
            base_dir = Path(__file__).parent
            db_path = base_dir / "data"
            if not db_path.exists():
                db_path.mkdir(parents=True)
            self.autoarknights_database_url = f"sqlite:///{db_path}/autoarknights.db"