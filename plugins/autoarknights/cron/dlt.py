#!/usr/bin/env python
import sqlite3
import time
import re
import base64
import os
import json
import traceback
import subprocess
import requests
from pathlib import Path
from collections import defaultdict
from collections import Counter
from collections import deque
from datetime import datetime
import fire


from pathlib import Path



# 图传配置，用于获取设备屏幕截图指定推送到群
SCREENSHOT_CONFIG = {
    "enable": True,  # 是否启用图传功能
    "server_url": "http://192.168.0.199:8888",  # 图传服务器地址
    "target_groups": ["-4687819227"],  # 目标群组列表
    "message_template": "设备状态截图 {device} \n时间: {time}"  
}


img_path = "tmp.jpg"
log_path = "log"
log_path = Path(log_path)
log_path.mkdir(exist_ok=True, parents=True)

serial_alias = {
    "1": "127.0.0.1:5557",
    "2": "127.0.0.1:5559",
}


daily_device = ["1"]
rg_device = ["1", "2", "0"]
oppid = "com.hypergryph.arknights"
bppid = "com.hypergryph.arknights.bilibili"


def take_screenshot(serial):
    """获取设备截图的具体实现"""
    try:
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 临时文件名
        temp_file = f"temp_screenshot_{serial.replace(':', '_')}.png"
        
        # 执行截图
        subprocess.run(["adb", "-s", serial, "shell", "screencap", "-p", f"/sdcard/{temp_file}"], 
                      capture_output=True)
        subprocess.run(["adb", "-s", serial, "pull", f"/sdcard/{temp_file}", temp_file],
                      capture_output=True)
        subprocess.run(["adb", "-s", serial, "shell", "rm", f"/sdcard/{temp_file}"],
                      capture_output=True)
        
        # 读取并转换为base64
        if os.path.exists(temp_file):
            with open(temp_file, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 删除临时文件
            os.remove(temp_file)
            
            # 发送到指定群
            for group in SCREENSHOT_CONFIG["target_groups"]:
                # 格式化消息
                info = SCREENSHOT_CONFIG["message_template"].format(
                    device=serial,
                    time=current_time
                )
                
                # 发送请求
                requests.post(
                    SCREENSHOT_CONFIG["server_url"],
                    data={
                        "to": f"g{group}",
                        "info": info,
                        "image": image_data
                    }
                )
            
            return True
            
        print("获取截图失败: 文件不存在")
        return False
            
    except Exception as e:
        print(f"截图失败: {str(e)}")
        return False




def mode(serial, f="help", *args, **kwargs):
    serial = str(serial)
    package = "com.bilabila.arknightsspeedrun2"
    packagehash = "3205c0ded576131ea255ad2bd38b0fb2"
    # package = "com.nx.nxproj.assist"
    # packagehash = "110625af36f2b330ccbaef8b987812df"
    path = Path("serial") / serial
    path.mkdir(exist_ok=True, parents=True)
    alias = serial
    if len(serial) < 4:
        serial = serial_alias[alias]

    def help():
        return

    def install(path=""):
        adb("install", path)

    # 设置图鉴用户名密码
    def captcha(username, password):
        x = load("config_debug.json")
        c(x, "captcha_username", username)
        c(x, "captcha_password", password)
        save("config_debug.json", x)


    def adb(*args):
        subprocess.run(["adb", "connect", serial], capture_output=True)
        out = subprocess.run(["adb", "-s", serial, *args], capture_output=True)
        # print("args",args)
        # print("out",out)

        return out.stdout.decode()

    def adbserial(*args):
        return serial

    def adbpull(name):
        adb("root")
        time.sleep(1)  # 等待 root 权限生效
        
        adb(
            "pull",
            "/data/data/" + package + "/assistdir/" + packagehash + "/root/" + name,
            path / name,
        )

    def adbpush(name):
        adb("root")
        time.sleep(1)  # 等待 root 权限生效

        adb(
            "push",
            path / name,
            "/data/data/" + package + "/assistdir/" + packagehash + "/root/" + name,
        )

    def arch():
        return adb(
            "shell",
            "getprop",
            "ro.product.cpu.abi",
        )

    def load(name):
        adbpull(name)
        p = path / name
        if not p.exists():
            with open(p, "w", encoding='utf-8') as f:
                f.write("{}")
        try:
            with open(path / name, encoding='utf-8') as f:
                return defaultdict(str, json.load(f))
        except:
            return defaultdict(str, {})


    def save(name, data):
        with open(path / name, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        adbpush(name)

    def c(data, key, value):
        if data[key] == value:
            return
        print(key, data[key], "=>", value)
        data[key] = value

    def free():
        return adb("shell", "free", "-h")

    def ps():
        return adb("shell", "ps|grep bila")

    def df():
        return adb("shell", "df -h")

    def rmpic(x=""):
        adb(
            "shell",
            "find",
            "/sdcard/" + package,
            "-type",
            "f",
            "-iname",
            "*" + str(x) + "*.jpg",
            "-delete",
        )

    def pic(name="", path=img_path, show=True, wait=False):
        path = Path(path)
        name = str(name)
        x = adb(
            "shell",
            "find",
            "/sdcard/" + package,
            "-iname",
            "*" + name + "*.jpg",
        )
        x = x.split("\n")
        x = list(sorted(filter(None, x)))
        for i in range(len(x)):
            print(Path(x[i]).stem)

        if path.exists():
            path.unlink()
        if len(x) == 0:
            print("未找到", name)
            if wait:
                return pic(name, path, show, wait)
            return
        adb(
            "pull",
            x[-1],
            path,
        )

        logfile = log_path / "pic.txt"
        logfile = open(logfile, "w")
        logfile.write(x[-1] + "\n")
        logfile.close()

        if show:
            subprocess.run(["feh", "--title", "float", path])

    def users(x):
        for x in filter(None, x.split("\n")):
            subprocess.run(["./dlt.py", "mode", serial, "user", x])


    def screenshot():
        """获取设备截图的封装函数"""
        return take_screenshot(serial)

    def get_merged_config(serial):
        """
        获取合并后的配置
        优先使用现有配置,缺失的部分用默认配置补充
        """
        import os
        
        # 获取当前脚本路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_config_path = os.path.join(script_dir, "config_multi_account_default.json")
        
        # 读取默认配置
        with open(default_config_path, encoding='utf-8') as f:
            default_config = defaultdict(str, json.load(f))
            
        # 读取当前配置
        current_config = load("config_multi_account.json")
        
        # 合并配置，使用当前配置覆盖默认配置
        merged_config = default_config.copy()
        merged_config.update(current_config)
        
        return merged_config

    def user(
        username=None,
        password=None,
        server=None,
        fight=None,
        idx=None,
        weekday_only=None,
        disable_drug=None,
        all_drug=None,
        norecruit=None,
        noactivity=None,
    ):

        # 加载合并后的配置
        x = get_merged_config(serial)
        
        # 强制设置一些基本参数
        x["multi_account_end_closeapp"] = True
        x["multi_account_end_closeotherapp"] = True
        x["multi_account_only_login"] = False
        x["multi_account_choice"] = "1-30"

        # 显示当前账号信息
        ans = ""
        first_empty_i = 0
        for i in range(1, 31):
            if (
                not str(x[f"username{i}"]).strip()
                or not str(x.get(f"password{i}", "")).strip()
            ):
                if first_empty_i == 0:
                    first_empty_i = i
                continue
                
            usernamei = x[f"username{i}"].replace("\s", "")
            passwordi = x.get(f"password{i}", "").strip()
            ans += (
                f"0 m {alias} user {usernamei} {passwordi}"
                + (" --server" if x.get(f"server{i}") == 1 else "")
                + (
                    (" --fight='" + x.get(f"multi_account_user{i}fight_ui", "1-7") + "'")
                    if x.get(f"multi_account_inherit_toggle{i}") == "独立设置"
                    else ""
                )
                + " --idx="
                + str(i)
                + "\n"
            )

        ans = ans.strip()
        logfile = open(log_path / "user.txt", "a")
        logfile.write(ans + "\n")
        logfile.close()
        print(ans)

        if not username or not password:
            username = ""
            password = ""

        if not username and not password and not idx:
            return
        if idx:
            first_empty_i = idx

        print("==> 添加至账号" + str(first_empty_i))

        # 修改配置
        x[f"username{first_empty_i}"] = str(username)
        x[f"password{first_empty_i}"] = str(password)
        x[f"multi_account_inherit_spinner{first_empty_i}"] = 0
        x[f"server{first_empty_i}"] = 1 if server else 0

        # 设置独立配置
        if fight or all_drug or disable_drug or norecruit or noactivity:
            x[f"multi_account_inherit_toggle{first_empty_i}"] = "独立设置"
            if fight:
                x[f"multi_account_user{first_empty_i}fight_ui"] = fight
            if disable_drug:
                x[f"multi_account_user{first_empty_i}max_drug_times"] = "-1"
            elif all_drug:
                x[f"multi_account_user{first_empty_i}max_drug_times"] = "99"
            if norecruit:
                x[f"multi_account_user{first_empty_i}auto_recruit0"] = False
                x[f"multi_account_user{first_empty_i}auto_recruit1"] = True 
                x[f"multi_account_user{first_empty_i}auto_recruit4"] = True
                x[f"multi_account_user{first_empty_i}auto_recruit5"] = True
                x[f"multi_account_user{first_empty_i}auto_recruit6"] = False
        else:
            x[f"multi_account_inherit_toggle{first_empty_i}"] = "继承设置"
        
        # 如果有账号存在,则启用多账号功能
        has_accounts = any(str(x[f"username{i}"]).strip() for i in range(1, 31))
        x["multi_account_enable"] = True if has_accounts else False

        save("config_multi_account.json", x)


    findNodeCache = None

    def findNode(text="", id="", cache=False):
        import xml.etree.ElementTree as ET

        nonlocal findNodeCache
        if cache:
            x = findNodeCache
        else:
            x = adb("exec-out", "uiautomator", "dump", "/dev/tty")
            x = re.search("(<.+>)", x)
        findNodeCache = x

        if not x:
            return
        x = x.group(1)
        tree = ET.XML(x)
        btn = None
        # ans = []
        for elem in tree.iter():
            elem = elem.attrib
            # print(elem)
            if (
                text
                and elem.get("text", None) == text
                or id
                and elem.get("resource-id", None) == id
            ):
                btn = elem.get("bounds", None)
                btn = re.search("(\d+)[^\d]+(\d+)[^\d]+(\d+)[^\d]+(\d+)", btn).groups()
                x = (int(btn[0]) + int(btn[2])) // 2
                y = (int(btn[1]) + int(btn[3])) // 2
                # print(text, x, y)
                return x, y
                # ans.append([x, y])
        # return ans

        # return ET.tostring(tree, encoding='unicode')

    def foreground():
        x = adb("shell", "dumpsys", "activity", "recents")
        x = re.search("Recent #0.*(com[^\s]+)", x)
        if x:
            return x.group(1)

        # | grep 'Recent #0' | cut -d= -f2 | sed 's| .*||' | cut -d '/' -f1

        # x = adb("shell", "dumpsys", "window", "windows")
        # x = re.search("mCurrentFocus=.* ([^ ]+)/(.+)", x)
        if x:
            return x.group(1)

    def stop(app=package):
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
        adb("shell", "am", "force-stop", app)

    def start():
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
        adb(
            "shell",
            "monkey",
            "-p",
            package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        )
        see_package = False
        for i in range(50):
            time.sleep(1)
            # print("foreground", foreground())
            # print("package",package)
            # print("see_package",see_package)
            if foreground() == package:
                findNode()
                ok = findNode("确定", cache=True)
                cancel = findNode("取消", cache=True)
                if cancel:
                    x, y = cancel
                    adb("shell", "input", "tap", str(x), str(y))
                elif ok:
                    x, y = ok
                    adb("shell", "input", "tap", str(x), str(y))
                    see_package = True
            snap = findNode("启动并定时",cache=True)
            #     id="com.bilabila.arknightsspeedrun2:id/switch_snap", cache=True
            # )
            if snap:
                 x, y = snap
                 adb("shell", "input", "tap", str(x), str(y))
            if foreground() == oppid or foreground() == bppid and see_package:
                break
            # elif see_package:
            #     break



    def check_device_online(serial):
        """检查设备是否在线
        
        Args:
            serial: 设备序列号/地址 (如 "127.0.0.1:5555")
            
        Returns:
            bool: 设备是否在线
        """
        try:
            # 尝试连接设备
            subprocess.run(["adb", "connect", serial], capture_output=True)
            # 获取设备列表
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            devices = result.stdout.strip().split('\n')[1:]
            
            # 检查当前设备是否在设备列表中
            for device in devices:
                if device.strip():
                    device_id = device.split('\t')[0]
                    if device_id == serial and 'device' in device:
                        return True
            return False
        except Exception as e:
            print(f"检查设备状态时出错: {str(e)}")
            return False        

    def parse_emulator_index(serial):
        """解析模拟器索引
        
        Args:
            serial: 设备序列号/地址
                
        Returns:
            int or None: 模拟器索引，如果无法解析则返回None
        """
        try:
            # 处理 emulator-xxxx 格式
            if serial.startswith('emulator-'):
                port = int(serial.split('-')[1])
                # 5555->0, 5556->1, 5557->2, 5558->3 ...
                return (port - 5555)
                
            # 处理 ip:port 格式
            if ':' in serial:
                port = int(serial.split(':')[1])
                if 5555 <= port <= 5585:
                    return (port - 5555)
                    
            return None
        except Exception as e:
            print(f"解析模拟器索引出错: {str(e)}")
            return None

    def is_ldplayer_port(serial):
        """判断是否是雷电模拟器的端口
        
        Args:
            serial: 设备序列号/地址
            
        Returns:
            bool: 是否是雷电模拟器端口
        """
        return parse_emulator_index(serial) is not None

    def restart_ldplayer(serial):
        """重启雷电模拟器
        
        Args:
            serial: 设备序列号/地址
            
        Returns:
            bool: 重启是否成功
        """
        try:
            # 检查是否是雷电模拟器端口
            index = parse_emulator_index(serial)
            if index is None:
                print(f"设备 {serial} 不是雷电模拟器或端口格式不正确")
                return False

            # 查找雷电模拟器路径
            possible_paths = [
                r"D:\gamertime\leidian\LDPlayer9\ldconsole.exe",
                # 可以继续添加其他可能的路径
            ]
            
            console_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    console_path = path
                    break
                    
            if not console_path:
                print(f"未找到雷电模拟器控制台程序")
                return False
                
            print(f"正在重启雷电模拟器 (index: {index})...")
            
            # 确保模拟器完全关闭
            subprocess.run([console_path, "quit", "--index", str(index)], 
                        capture_output=True)
            
            # 等待进程完全退出
            time.sleep(5)
            
            # 再次检查并强制结束
            subprocess.run([console_path, "quitall"], capture_output=True)
            time.sleep(5)
            
            # 启动模拟器
            subprocess.run([console_path, "launch", "--index", str(index)], 
                        capture_output=True)
            
            # 等待模拟器启动完成
            max_wait = 60
            start_time = time.time()
            while time.time() - start_time < max_wait:
                result = subprocess.run([console_path, "isrunning", "--index", str(index)], 
                                    capture_output=True, text=True)
                if "running" in result.stdout.lower():
                    # 额外等待确保系统完全启动
                    time.sleep(10)
                    return True
                time.sleep(2)
            
            print("模拟器启动超时")
            return False
            
        except Exception as e:
            print(f"重启模拟器时出错: {str(e)}")
            return False

    def ensure_device_online(serial, max_retries=3):
        """确保设备在线，必要时重启模拟器
        
        Args:
            serial: 设备序列号/地址
            max_retries: 最大重试次数
            
        Returns:
            bool: 设备是否最终在线
        """
        retry_count = 0
        while retry_count < max_retries:
            if check_device_online(serial):
                return True
                
            # 只有确认是雷电模拟器端口时才尝试重启
            if is_ldplayer_port(serial):
                print(f"设备离线，尝试重启模拟器... ({retry_count + 1}/{max_retries})")

                if restart_ldplayer(serial):
                    time.sleep(10)
                    if check_device_online(serial):
                        return True
            else:
                print(f"设备 {serial} 不是雷电模拟器或端口格式不正确，跳过重启")
                return False
                    
            retry_count += 1
            time.sleep(5)
        
        print(f"设备 {serial} 连接失败")
        return False

    def sync_db_config():
        """从数据库同步设备的账号配置"""
        try:
            print(f"正在从数据库读取配置...")
            
            # 获取数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            db_path = os.path.join(parent_dir, "data", "autoarknights.db")
            
            # 加载合并后的配置
            x = get_merged_config(serial)
            
            # 连接数据库
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            device=alias
            # 查询账号，按创建时间排序
            cursor.execute("""
                SELECT * FROM arkaccount 
                WHERE device = ? AND is_frozen = 0
                ORDER BY created_at ASC
            """, (device,))
                    
            accounts = cursor.fetchall()
            
            if not accounts:
                print(f"未找到设备 {alias} 的账号配置")
                return
                
            print(f"找到 {len(accounts)} 个账号配置")

            # 初始化配置
            for i in range(1, 31):
                x[f"username{i}"] = ""
                x[f"password{i}"] = ""
                x[f"server{i}"] = 0

            # 按顺序添加账号配置
            current_index = 1
            for account in accounts:
                username = account['username']
                password = account['password']
                server_type = 1 if account['server'] == 'bilibili' else 0
                
                print(f"正在更新账号 {username} 到位置 {current_index}")
                
                # 基本账号信息
                c(x, f"username{current_index}", username)
                c(x, f"password{current_index}", password)
                c(x, f"server{current_index}", server_type)
                
                # 获取账号对应的配置
                cursor.execute("""
                    SELECT * FROM arkconfig 
                    WHERE username = ?
                """, (username,))
                
                config = cursor.fetchone()
                if not config:
                    print(f"账号 {username} 未找到配置，使用默认设置")
                    current_index += 1
                    continue

                # 同步基础配置
                c(x, f"multi_account_user{current_index}fight_ui", config['fight_stages'])
                c(x, f"multi_account_user{current_index}max_drug_times", str(config['max_drug_times']))
                c(x, f"multi_account_user{current_index}max_stone_times", str(config['max_stone_times']))
                
                try:
                    # 解析JSON配置
                    auto_recruit_config = json.loads(config['auto_recruit_config'])
                    shop_config = json.loads(config['shop_config'])
                    task_config = json.loads(config['task_config'])
                    
                    # 同步公招配置
                    for key in ["auto_recruit0", "auto_recruit1", "auto_recruit4", "auto_recruit5", "auto_recruit6"]:
                        if key in auto_recruit_config:
                            c(x, f"multi_account_user{current_index}{key}", auto_recruit_config[key])
                    
                    # 同步商店配置
                    if "high_priority" in shop_config:
                        c(x, f"multi_account_user{current_index}high_priority_goods", shop_config["high_priority"])
                    if "low_priority" in shop_config:
                        c(x, f"multi_account_user{current_index}low_priority_goods", shop_config["low_priority"])
                    
                    # 同步任务配置
                    task_keys = {
                        "collect_mail": "1",        # 收邮件
                        "battle_loop": "2",         # 循环战斗 
                        "auto_recruit": "3",        # 自动公招
                        "visit_friends": "4",       # 访问好友
                        "base_collect": "5",        # 基建收获
                        "base_shift": "6",          # 基建换班
                        "manufacture_boost": "7",    # 制造加速
                        "clue_exchange": "8",       # 线索交流
                        "deputy_change": "9",       # 副手换人
                        "credit_shop": "10",        # 信用购买
                        "public_recruit": "11",     # 公开招募
                        "mission_collect": "12",    # 任务收集
                        "time_limited": "13",       # 限时任务
                        "shop_purchase": "14",      # 商店购买
                        "story_unlock": "15",       # 故事解锁
                        "skland_checkin": "16"      # 森空岛签到
                    }
                    
                    # 更新任务配置
                    for i in range(1, 17):  # 默认开启所有任务
                        c(x, f"multi_account_user{current_index}now_job_ui{i}", True)
                        
                    for db_key, ui_num in task_keys.items():
                        if db_key in task_config:
                            c(x, f"multi_account_user{current_index}now_job_ui{ui_num}", task_config[db_key])
                    
                    # 同步继承设置
                    c(x, f"multi_account_inherit_toggle{current_index}", 
                    "独立设置" if not config['inherit_settings'] else "继承设置")
                    
                except json.JSONDecodeError as e:
                    print(f"账号 {username} 配置JSON解析失败: {str(e)}")
                    current_index += 1
                    continue
                    
                current_index += 1

            # 启用多账号功能
            x["multi_account_enable"] = True
            x["multi_account_end_closeapp"] = True 
            x["multi_account_end_closeotherapp"] = True
            x["multi_account_only_login"] = False
            x["multi_account_choice"] = "1-30"

            # 保存配置
            save("config_multi_account.json", x)
            print("配置同步完成")
            conn.close()

        except Exception as e:
            print(f"配置同步出错: {str(e)}")
            traceback.print_exc()
            if 'conn' in locals():
                conn.close()

    def restart(account="", hide=True, rg=False, crontab=False, game=False):
        """重启应用程序
            
        Returns:
            bool: 重启是否成功
        """
        # 确保设备在线
        if not ensure_device_online(serial):
            return False

        # 原有的重启逻辑
        if account:
            x = load("config_multi_account.json")
            c(
                x,
                "multi_account_choice",
                x["multi_account_choice"].split("#")[0] + "#" + str(account),
            )
            save("config_multi_account.json", x)

        if game:
            stop(oppid)
            stop(bppid)
        stop()
        start()
        
        return True

    def show():
        subprocess.run(["adb", "connect", serial], capture_output=True)
        print("serial", serial)
        subprocess.run(["scrcpy", "-s", serial], capture_output=True)

    def qq(qq=""):
        if not qq:
            return
        x = load("config_debug.json")
        c(x, "QQ", qq)
        save("config_debug.json", x)

    def normal(qq=None, weekday_only=None, fight=None):
        x = load("config_main.json")
        c(x, "fight_ui", fight or "jm hd ce ls ap pr")
        for i in range(1, 13):
            c(x, f"now_job_ui" + str(i), True)
        c(x, f"now_job_ui8", False)
        c(x, f"crontab_text", "4:00 12:00 20:00")
        c(x, f"auto_recruit0", True)
        c(x, f"auto_recruit4", True)
        c(x, f"auto_recruit5", True)
        c(x, f"auto_recruit6", False)
        c(x, f"low_priority_goods", "")
        save("config_main.json", x)

        x = load("config_debug.json")
        c(x, "max_jmfight_times", "1")
        c(x, "max_login_times_5min", "3")

        if qq:
            c(x, "QQ", f"{qq}#{alias}")
        c(
            x,
            "multi_account_choice_weekday_only",
            weekday_only or x["multi_account_choice_weekday_only"],
        )
        c(x, "qqnotify_beforemail", True)
        c(x, "qqnotify_afterenter", True)
        c(x, "qqnotify_beforeleaving", True)
        c(x, "qqnotify_beforemission", True)
        c(x, "qqnotify_save", True)
        c(x, "collect_beforeleaving", True)
        # 一是完成日常任务，二是间隔时间最长可以11小时，提高容错
        c(x, "zero_san_after_fight", True)
        c(x, "max_drug_times_" + str(1) + "day", "99")
        c(x, "max_drug_times_" + str(2) + "day", "99")
        c(x, "max_drug_times_" + str(3) + "day", "8")
        c(x, "max_drug_times_" + str(4) + "day", "4")
        c(x, "max_drug_times_" + str(5) + "day", "2")
        c(x, "max_drug_times_" + str(6) + "day", "1")
        c(x, "max_drug_times_" + str(7) + "day", "1")
        c(x, "enable_log", False)
        # c(x, "enable_disable_lmk", False)
        # c(x, "disable_killacc", False)
        # c(x, "enable_restart_package", True)
        c(x, "restart_package_interval", "3600")
        # c(x, "tap_wait", "")
        save("config_debug.json", x)

        x = load("config_multi_account.json")
        c(x, "multi_account_end_closeotherapp", True)
        c(x, "multi_account_end_closeapp", True)
        c(x, "multi_account_choice", "1-30")
        c(x, "multi_account_enable", True)
        save("config_multi_account.json", x)

    def soft():
        x = load("config_debug.json")
        c(x, "max_login_times_5min", "1")
        save("config_debug.json", x)

    def hard():
        x = load("config_debug.json")
        c(x, "max_login_times_5min", "3")
        save("config_debug.json", x)

    def lmk(value=""):
        print(adb("shell", "cat", "/sys/module/lowmemorykiller/parameters/minfree"))
        if value:
            adb(
                "shell",
                "echo",
                value,
                ">",
                "/sys/module/lowmemorykiller/parameters/minfree",
            )
        return adb("shell", "cat", "/sys/module/lowmemorykiller/parameters/minfree")

    def top():
        return adb("shell", "top", "-s", "rss", "-m", "10", "-n", "1")

    return locals()[f](*args, **kwargs)


m = mode
o = lambda *args, **kwargs: DLT().order(*args, **kwargs)
d = lambda *args, **kwargs: DLT().detail(*args, **kwargs)


def daily(*args, **kwargs):
    for device in daily_device:
        # print("args",args)
        # print("device",deice)
        # mode(device, *args, **kwargs)
        print("==>", device, *args)
        print(mode(device, *args, **kwargs))


def check(key="", show=True):
    user = []
    user2device = {}
    user2idx = {}
    serial2user = {}
    device_account = []
    dlt = DLT()
    for device in daily_device:
        y = mode(device, "load", "config_multi_account.json")
        for i in range(1, 31):
            if (
                not str(y["username" + str(i)]).strip()
                or not str(y["password" + str(i)]).strip()
            ):
                continue
            username = y["username" + str(i)].strip()
            password = y["password" + str(i)].strip()
            if username in my_account:
                user2device[username] = device
                continue
            serial = dlt.all2serial(username + " " + password + " ", quiet=True)
            # serial = dlt.all2serial(password + " ", quiet=True)
            # if not serial :
            #
            #     serial = dlt.all2serial( " " +password + " "+username, quiet=True)
            if not serial:
                print("all2serial not found", password)
                continue
            user.append(username)
            user2device[username] = device
            user2idx[username] = i
            if type(serial) == list:
                for serial in serial:
                    serial2user[serial] = username
                    device_account.append(serial)
            else:
                serial2user[serial] = username
                device_account.append(serial)
    if key:
        serial = dlt.all2serial(key)
        if type(serial) == list:
            serial = serial[0]
        user = serial2user[serial]
        device = user2device[user]
        # print("serial", serial)
        # print("user", user)
        # exit()
        mode(device, "pic", user + "\ *分钟", show=show)

        return

    dlt_account = []
    dlt_wait_account = []
    for m in dlt.my(raw=True):
        dlt_account.append(m["SerialNo"])
    for m in dlt.my(raw=True, status=13):
        dlt_account.append(m["SerialNo"])
        dlt_wait_account.append(m["SerialNo"])
    for m in dlt.my(raw=True, status=14):
        dlt_account.append(m["SerialNo"])
        dlt_wait_account.append(m["SerialNo"])

    dev_set = set(device_account)
    if len(dev_set) != len(device_account):
        dup = [item for item, count in Counter(device_account).items() if count > 1]
        for serial in dup:
            print(
                user2device[serial2user[serial]],
                serial2user[serial],
                user2idx[serial2user[serial]],
            )

        return

    dlt_set = set(dlt_account)
    assert len(dlt_set) == len(dlt_account)

    waste_set = dev_set - dlt_set
    print("==> total", len(dev_set))

    # print("user2device", user2device)
    # print(
    #     "Counter(user2device.values()).most_common()",
    #     Counter(user2device.values()).most_common(),
    # )
    next_device = Counter(user2device.values()).most_common()[-1][0]

    print("==> waste_set", waste_set)
    for serial in waste_set:
        print(dlt.detail(serial, quiet=True))
    for serial in waste_set:
        user = serial2user[serial]
        print(f"0 m {user2device[user]} user {user} '' --idx={user2idx[user]}")

    print("==> over_set")
    over_set = []
    for m in dlt.my(raw=True):
        leave_time = float(m["LeaveTime"][:-2])
        if leave_time < 16:
            serial = m["SerialNo"]
            print(dlt.detail(serial, quiet=True))
            print("0 check " + serial + ";" + "0 last " + serial + " --over")

    insane_set = dlt_set - dev_set
    print("==> insane_set", insane_set)
    for serial in insane_set:
        if serial in dlt_wait_account:
            continue
        print(f"0 m {next_device} user", end=" ")
        print(dlt.detail(serial, quiet=True))


# every day upload
def edu(show=False):
    dlt = DLT()
    for m in dlt.my(raw=True):
        if not DLT.need_everyday_upload(m["Title"]):
            continue
        if m["SerialNo"] in everyday_upload_blacklist:
            continue

        print(m["Title"])
        try:
            check(m["SerialNo"], show=show)
            dlt.submit(m["SerialNo"], show=show)
        except Exception:
            pass
    for username in extra_everyday_upload:
        try:
            check(username, show=show)
            dlt.submit(username, show=show)
        except Exception:
            pass


def users():
    daily("user")


def newsession():
    resp = requests.get(
        "http://api.vc.bilibili.com/session_svr/v1/session_svr/new_sessions",
        cookies={"SESSDATA": bilibili_sessdata},
    )
    r = json.loads(resp.text)
    # r = r['data']['session_list']
    r = r["data"]["session_list"]
    ans = []
    for s in r:
        x = {
            "talker_id": s["talker_id"],
            "session_type": s["session_type"],
        }
        content = s["last_msg"]["content"]
        content = json.loads(content)
        content = content["content"]
        server = 0
        p = "(B|b)[^ ]*服"
        if re.search(p, content):
            content = re.sub(p, "", content)
            server = 1
        content = re.sub("账号[:：]*", "", content)
        content = re.sub("密码[:：]*", "", content)
        user = re.search("([^ ]+)\s+([^ ]+)", content)
        if not user:
            continue
        username = user.group(1)
        password = user.group(2)
        x["username"] = username
        x["password"] = password
        x["server"] = server
        ans.append(x)

    return ans


def session():
    cur = deque()
    new = newsession()
    for n in reversed(new):
        for c in cur:
            if c["username"] == n["username"]:
                c["password"] = n["password"]
                c["server"] = n["server"]
                break
        else:
            cur.push(n)


# https://github.com/Nemo2011/bilibili-api/blob/bd95dcb19e598462b08983438fa87f5570045f48/bilibili_api/login.py
def bilibili_login(username: str, password: str):
    from bilibili_api.login import (
        login_with_password,
        API,
        httpx,
        json,
        encrypt,
        to_form_urlencoded,
        time,
        hashlib,
        uuid,
    )

    # from bilibili_api.user import get_self_info
    # from bilibili_api import settings
    # from bilibili_api import sync
    # ans = login_with_password(username,password)
    # __import__('pdb').set_trace()
    # from bilibili_api

    api_token = API["password"]["get_token"]
    sess = httpx.Client()
    token_data = json.loads(sess.get(api_token["url"]).text)
    hash_ = token_data["data"]["hash"]
    key = token_data["data"]["key"]
    final_password = encrypt(hash_, key, password)
    login_api = API["password"]["login"]
    appkey = "bca7e84c2d947ac6"
    appsec = "60698ba2f68e01ce44738920a0ffe768"
    datas = {
        "actionKey": "appkey",
        "appkey": appkey,
        "build": 6270200,
        "captcha": "",
        "challenge": "",
        "channel": "bili",
        "device": "phone",
        "mobi_app": "android",
        "password": final_password,
        "permission": "ALL",
        "platform": "android",
        "seccode": "",
        "subid": 1,
        "ts": int(time.time()),
        "username": username,
        "validate": "",
    }
    form_urlencoded = to_form_urlencoded(datas)
    md5_string = form_urlencoded + appsec
    hasher = hashlib.md5(md5_string.encode(encoding="utf-8"))
    datas["sign"] = hasher.hexdigest()
    login_data = json.loads(
        sess.request(
            "POST",
            login_api["url"],
            data=datas,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://passport.bilibili.com/login",
            },
            cookies={"buvid3": str(uuid.uuid1())},
        ).text
    )
    return login_data
    # __import__('pdb').set_trace()


def official_login(username, password):
    import requests

    res = requests.post(
        "https://as.hypergryph.com/user/auth/v1/token_by_phone_password",
        json={"phone": str(username), "password": str(password)},
    ).json()
    return res


def account_exist(username: str, password: str, server=False):
    if server:
        login_data = bilibili_login(username, password)
        print(login_data)
        if login_data["code"] == 0:
            return True
        else:
            return False
    else:
        login_data = official_login(username, password)
        print(login_data)
        if login_data.get("status", -1) in (0, 1):
            return True
        else:
            return False


if __name__ == "__main__":
    fire.Fire()