# nonebot plugin for arklights
# 明日方舟速通nonebot插件指北
1.为什么会诞生此插件？
懒得上号不抽卡了因为抽卡歪了气的搓出来的。这样就可以~~不登号~~不抽卡了（雾）
2.插件工作原理？
对接明日方舟速通https://github.com/AegirTech/ArkLights 本质上是通过明日方舟速通原有的dlt.py进行的云控，其实就是更新被控端的配置文件，然后交给速通自己去运行
3.部署碎碎念---
代码质量差，由愚蠢的gpt和我愚蠢的我共同完成，本来设想实在云电脑上部署，或者通过云手机加云服务器实现远程控制，后来转念一想直接真机部署不是美哉？立刻捡了一个RK3399的垃圾开始动手，也是直接撅醒了
![image](https://github.com/user-attachments/assets/b5580674-0e7b-4511-b771-331aa0cab777)

#部署教程
1.部署准备
一个可用的linux客户端？（推荐使用root后的手机直接本地部署例如magisk的proot ubuntu模块，或者直接一机控多个个手机或者模拟器，（除非你要接单呵呵呵呵））一个可用的adb手机受控端，安装了明日方舟和明日方舟速通。

2.下载本仓库
克隆本仓库，并安装依赖(下载速度慢问题和镜像问题自行解决，)
    git clone https://github.com/frlda/autoarknights.git
	pip install -r requirements.txt
 
3.获取onebot无头QQ
  推荐使用lagrange onebot，https://lagrangedev.github.io/Lagrange.Doc/ 
内存占用小且适合在各种设备部署。部署教程配置这里不做解释，本bot可以单用作插件（应该）也可以直接单走。直接单走的话用的是正向websocket连接，默认6700端口，请自行配置env

4.配置config
配置位于plugins/autoarknights/cron下的dlt.py，把你的设备adb端口号输进去。
![image](https://github.com/user-attachments/assets/c3c713bf-079a-4ddb-b337-7eff6ba3d5a0)

配置位于plugins/autoarknights下的config.py，看需求设置
配置明日方舟速通，设置好打码的图鉴账号密码，还有qq通知的账号和地址，请参照插件中的qqimage deliver进行图传设置（这个也开放了端口的），然后把明日方舟速通切换到多号模式，启动再关闭（这是为了让速通进入多账号模式能被正常拉起）

5.启动
    python bot.py    
	./Lagrange.OneBot
请向你登录的bot发送 在吗 进行测试，正常会回复 我在博士

6.使用
发送方舟help 获取帮助与使用
绑定账号后一定要设置对应的前面输入的adb设备端口序号
![8d04025ad3cb0900dd48c8f0e40663d7](https://github.com/user-attachments/assets/498e4333-0ba4-43d8-8ede-c053a50deead)
![3b5296cf0df2eeb9b1831918cc358623](https://github.com/user-attachments/assets/f24a91df-954b-4ce5-9903-8adfe9b03509)
![image](https://github.com/user-attachments/assets/9e15aa74-46cb-4c85-8dbd-67a5b4f4d134)

~~写的很简略嘻嘻，扣1写fmx1_pro rk3399完整部署教程~~
