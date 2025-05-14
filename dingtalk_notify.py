import os
import requests
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import logging
import datetime
from configparser import ConfigParser

class DingTalkNotifier:
    def __init__(self):
        """初始化钉钉机器人"""
        self.config = ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
        self.webhook_url = self.config.get('dingtalk', 'webhook_url')
        self.secret = self.config.get('dingtalk', 'secret', fallback=None)
        
        # 配置日志
        log_file = os.path.join(os.path.dirname(__file__), "dingtalk_notify.log")
        try:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
        except Exception as e:
            print(f"无法创建日志文件: {e}")
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler()]
            )
    
    def send_notification(self, title, content, post_url):
        """发送钉钉通知"""
        try:
            message = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}\n\n查看详情: {post_url}"
                }
            }
            timestamp = str(round(time.time() * 1000))
            secret_enc = self.secret.encode('utf-8')
            string_to_sign = '{}\n{}'.format(timestamp, self.secret)
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                self.webhook_url+"&timestamp="+timestamp+"&sign="+sign,
                headers=headers,
                data=json.dumps(message),
                timeout=10
            )
            
            if response.status_code == 200:
                logging.info(f"成功发送钉钉通知: {title}")
                return True
            else:
                logging.error(f"发送钉钉通知失败: {response.text}")
                return False
        except Exception as e:
            logging.error(f"发送钉钉通知时出错: {e}")
            return False

# 全局实例
NOTIFIER = DingTalkNotifier()

def notify_new_post(post_data, is_update=False):
    """推送新帖子通知
    :param post_data: 帖子数据
    :param is_update: 是否为更新通知
    """
    # 兼容不同数据结构格式
    prefix = "[更新] " if is_update else ""
    title = f"{prefix}新帖子: {post_data.get('title', post_data.get('subject', '无标题'))}"
    content = post_data.get('content', '无内容')
    content = content[:100] + "..." if len(content) > 100 else content
    
    # 添加时间戳
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"{content}\n\n更新时间: {timestamp}" if is_update else f"{content}\n\n发布时间: {timestamp}"
    
    url = post_data.get('url', f"https://www.miyoushe.com/sr/article/{post_data.get('post_id', '')}")
    return NOTIFIER.send_notification(title, content, url)