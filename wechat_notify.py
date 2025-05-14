import requests
import json
import logging
from configparser import ConfigParser
from datetime import datetime

class WeChatNotifier:
    def __init__(self):
        """初始化企业微信机器人"""
        self.config = ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
        self.webhook_url = self.config.get('wechat', 'webhook_url')
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("wechat_notify.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def send_notification(self, title, content, post_url):
        """发送企业微信通知"""
        try:
            message = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}\n\n查看详情: {post_url}\n\n推送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                self.webhook_url,
                headers=headers,
                data=json.dumps(message),
                timeout=10
            )
            
            if response.status_code == 200:
                logging.info(f"成功发送企业微信通知: {title}")
                return True
            else:
                logging.error(f"发送企业微信通知失败: {response.text}")
                return False
        except Exception as e:
            logging.error(f"发送企业微信通知时出错: {e}")
            return False

# 全局实例
NOTIFIER = WeChatNotifier()

def notify_new_post(post_data):
    """推送新帖子通知"""
    # 兼容不同数据结构格式
    title = f"新帖子: {post_data.get('title', post_data.get('subject', '无标题'))}"
    content = post_data.get('content', '无内容')
    content = content[:100] + "..." if len(content) > 100 else content
    url = post_data.get('url', f"https://www.miyoushe.com/sr/article/{post_data.get('post_id', '')}")
    return NOTIFIER.send_notification(title, content, url)