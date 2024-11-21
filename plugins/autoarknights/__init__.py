from nonebot.plugin import PluginMetadata
from .handlers import *
from .image_deliver import *  

__plugin_meta__ = PluginMetadata(
    name="autoarknights",
    description="明日方舟账号管理插件",
    usage="""
    账号管理:
    - 绑定游戏账号 [账号] [密码] [服务器]
    - 删除游戏账号 [账号序号]
    - 查看账号列表
    - 账号设置 [账号序号] [功能] [开关或值]
    ...
    """,
    type="application",
    homepage="https://github.com/frinda/nonebot-plugin-autoarknights",
    supported_adapters={"~onebot.v11"},
)