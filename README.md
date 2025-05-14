# 米游社帖子监控系统
（本项目全部内容均为AI开发，暂时只做了崩坏星穹铁道攻略区以及候车区的，后续会把其他所有区的加上并且尝试做网站方便使用）

## 项目简介
这是一个用于监控米游社崩坏星穹铁道板块的帖子监控系统。它可以自动检测并筛选出包含特定关键词的帖子，并通过钉钉和企业微信机器人发送通知，帮助玩家及时了解社区动态。

## 功能特性
- 🔍 自动监控米游社星穹铁道板块的新帖子
- 🎯 支持自定义关键词过滤
- 📱 支持钉钉和企业微信机器人通知
- 💾 本地数据库存储帖子信息
- 🔄 自动检测帖子更新
- 🌐 智能网络重试机制
- 📊 支持数据导出功能

## 技术架构
- 开发语言：Python 3.8+
- 数据存储：SQLite
- 网络请求：requests
- 配置管理：configparser
- 日志系统：logging

## 安装部署
1. 克隆项目到本地
```bash
git clone [项目地址]
cd [项目目录]
```

2. 安装依赖包
```bash
pip install -r requirements.txt
```

3. 配置文件设置
复制`config.ini`文件，并按需修改配置：
```ini
[database]
db_path = posts.db

[crawler]
forum_ids = 52,61  # 52为候车室，61为攻略区

[keywords]
keywords = 求助,提问,求问  # 自定义关键词，用逗号分隔

[dingtalk]
webhook_url = 你的钉钉机器人webhook地址
secret = 你的钉钉机器人密钥

[wechat]
webhook_url = 你的企业微信机器人webhook地址
```

## 使用说明

### 启动监控
```bash
python mysshijian.py
```

### 查看数据
```bash
python sr_data_viewer.py
```

### 配置说明

#### 钉钉机器人配置
1. 在钉钉群中添加自定义机器人
2. 获取webhook地址和加签密钥
3. 将信息填入config.ini的[dingtalk]部分

#### 企业微信机器人配置
1. 在企业微信群中添加机器人
2. 获取webhook地址
3. 将地址填入config.ini的[wechat]部分

#### 自定义关键词
在config.ini的[keywords]部分添加关键词，多个关键词用逗号分隔：
```ini
[keywords]
keywords = 求助,提问,求问,攻略
```

## 项目结构
```
├── mysshijian.py      # 主程序
├── db_handler.py      # 数据库处理模块
├── dingtalk_notify.py # 钉钉通知模块
├── wechat_notify.py   # 企业微信通知模块
├── config.ini        # 配置文件
└── sr_data_viewer.py  # 数据查看器
```

## 注意事项
- 请确保网络环境稳定
- 建议使用代理时，先测试代理的可用性
- 定期备份数据库文件
- 遵守米游社的访问频率限制

## 常见问题
1. 如何修改监控间隔？
   - 在主程序中修改time.sleep()的参数值（默认30秒）

2. 如何导出数据？
   - 使用sr_data_viewer.py的导出功能

3. 网络连接失败怎么办？
   - 检查网络连接
   - 确认代理配置是否正确
   - 查看日志文件排查问题

## 贡献指南
欢迎提交Issue和Pull Request来帮助改进项目。

## 许可证
MIT License
