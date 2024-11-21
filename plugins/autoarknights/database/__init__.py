from pathlib import Path
from sqlmodel import create_engine, Session, SQLModel
from nonebot import get_driver

driver = get_driver()

# 获取插件数据目录
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data"
if not DB_PATH.exists():
    DB_PATH.mkdir(parents=True)

DATABASE_URL = f"sqlite:///{DB_PATH}/autoarknights.db"
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    return Session(engine)

@driver.on_startup
async def init_database():
    SQLModel.metadata.create_all(engine)

from .models import ArkAccount,ArkConfig,ArkConfigHistory