import nonebot
from nonebot.adapters.telegram import Adapter as TelegramAdapter
from nonebot.adapters.telegram import Adapter



nonebot.init()
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(TelegramAdapter)

# 加载插件
nonebot.load_builtin_plugins("echo")  # nonebot测试插件
nonebot.load_plugin("nonebot_plugin_orm")
nonebot.load_plugin("nonebot_plugin_apscheduler")

# 加载自定义插件
nonebot.load_plugins("plugins/autoarknights")

if __name__ == "__main__":
    nonebot.logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run(app="__mp_main__:app")
