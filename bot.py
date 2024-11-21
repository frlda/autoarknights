import nonebot
from nonebot.adapters.onebot.v11 import Adapter


nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

# 加载插件
nonebot.load_builtin_plugins("echo")#nonebot测试插件
nonebot.load_plugin("nonebot_plugin_orm")
nonebot.load_plugin("nonebot_plugin_apscheduler")

nonebot.load_plugins("autoarknights/plugins")
nonebot.load_plugins("plugins/autoarknights")

if __name__ == "__main__":
    nonebot.run()