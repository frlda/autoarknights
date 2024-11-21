from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Message
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from nonebot.adapters import Bot, Event

__plugin_meta__ = PluginMetadata(
    name="在线状态",
    description="当用户发送'在吗'时回复'在的博士'",
    usage="发送：在吗",
    type="application",
    homepage="https://github.com/frinda/nonebot-online-plugin",
    supported_adapters={"~onebot.v11"},
)

# "在吗"
online = on_keyword({"在吗"}, priority=10)

@online.handle()
async def handle_online(bot: Bot, event: Event, state: T_State):
    await online.finish(Message("我在,博士"))