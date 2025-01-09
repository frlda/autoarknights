from nonebot import on_command, on_keyword
from nonebot.adapters.telegram import Bot, Message, Event
from nonebot.plugin import PluginMetadata


# 测试命令
test = on_command("test", priority=1)
hello = on_keyword({"hello"}, priority=2)

@test.handle()
async def handle_test(bot: Bot, event: Event):
    """处理 /test 命令"""
    await test.finish("测试成功！机器人正常工作中...")

@hello.handle()
async def handle_hello(bot: Bot, event: Event):
    """处理 hello 关键词"""
    await hello.finish("Hello! 我在这里！")

