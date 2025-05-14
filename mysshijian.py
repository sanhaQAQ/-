import time
import requests
import os
import datetime
import socket
import logging
import configparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from db_handler import DBHandler

# 加载配置文件
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

# 初始化数据库
DB = DBHandler(config['database']['db_path'])

# 从配置获取论坛ID
forum_ids = [int(id.strip()) for id in config['crawler']['forum_ids'].split(',')]
cached_post_id = {id: [] for id in forum_ids}
# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("miyoushe_monitor.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 网络配置
CONNECTION_TIMEOUT = 15  # 连接超时时间（秒）
READ_TIMEOUT = 30  # 读取超时时间（秒）

# 代理设置（如果需要使用代理，取消下面的注释并填入代理地址）
# 禁用代理，因为日志显示代理连接问题
PROXIES = None
# 如果需要使用代理，可以取消注释下面的代码
# PROXIES = {
#     "http": "http://127.0.0.1:7897",
#     "https": "http://127.0.0.1:7897"
# }

# 创建会话并配置重试策略
session = requests.Session()
retry_strategy = Retry(
    total=3,  # 总重试次数
    backoff_factor=1,  # 重试间隔因子
    status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
    allowed_methods=["GET", "POST"]  # 允许重试的请求方法
)
session.mount("http://", HTTPAdapter(max_retries=retry_strategy))
session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

# 如果配置了代理，则使用代理
if PROXIES:
    session.proxies.update(PROXIES)

# 添加必要的请求头信息
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.miyoushe.com/sr/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.miyoushe.com"
}
# 自定义关键词列表
keywords = [
    "求助", 
    "提问",      
    "求问", 
    "问问", 
]

post_ids = []
def check_internet_connection():
    """检查互联网连接状态"""
    try:
        # 尝试连接到百度（作为检测网络连接的参考点）
        socket.create_connection(("baidu.com", 80), timeout=5)
        return True
    except OSError:
        return False

def get_posts(forum_id, sort_type=1):
    """
    获取论坛帖子
    :param forum_id: 论坛ID
    :param sort_type: 排序方式 1=最新回复(默认) 2=最新发布
    :return: 匹配关键词的帖子列表
    """
    # 首先检查网络连接
    if not check_internet_connection():
        logging.error("网络连接不可用，请检查您的网络设置")
        # 返回None表示连接失败，与空列表区分开
        return None
        
    # 构建请求URL
    url = f"https://bbs-api.miyoushe.com/painter/wapi/getRecentForumPostList?forum_id={forum_id}&gids=6&is_good=false&page_size=20&sort_type={sort_type}"
    post_data = None
    try:
        logging.info(f"正在请求: {url}")
        response = session.get(
            url, 
            headers=headers, 
            timeout=(CONNECTION_TIMEOUT, READ_TIMEOUT)  # 使用元组设置连接超时和读取超时
        )
        response.raise_for_status()  # 检查HTTP状态码
        post_data = response.json()
        
        # 记录API响应内容，便于调试
        logging.debug(f"API响应内容: {post_data}")
        
        # 检查响应数据结构
        if "data" not in post_data or "list" not in post_data["data"]:
            logging.warning(f"响应数据结构异常: 缺少必要字段")
            return []
        
        logging.info(f"成功获取论坛 {forum_id} 的帖子数据")
    except requests.exceptions.Timeout:
        logging.error(f"请求超时: {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP错误: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        logging.error(f"连接错误: 无法连接到服务器 - {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"请求异常: {e}")
        return None
    except ValueError as e:
        logging.error(f"JSON解析错误: {e}")
        return None
    
    # 如果没有成功获取数据，直接返回None表示连接或数据结构异常
    if not post_data or "data" not in post_data or "list" not in post_data["data"]:
        logging.warning(f"响应数据结构异常或为空")
        return None
        
    hitted_post = []
    for post in post_data["data"]["list"]:
        if post["post"]["post_id"] not in cached_post_id[forum_id]:
            post_ids.append(post["post"]["post_id"])
            
            # 记录每个帖子的内容，便于分析
            logging.debug(f"新帖子ID: {post['post']['post_id']}")
            logging.debug(f"标题: {post['post']['subject']}")
            
            # 检查关键词匹配
            matched_keywords = []
            for keyword in keywords:
                if keyword in post["post"]["subject"] or keyword in post["post"]["content"]:
                    matched_keywords.append(keyword)
                    
            if matched_keywords:
                logging.info(f"帖子 {post['post']['post_id']} 匹配关键词: {', '.join(matched_keywords)}")
                hitted_post.append(post)
    
    cached_post_id[forum_id] = post_ids
    return hitted_post
def save_to_database(posts):
    """将帖子数据保存到数据库"""
    if not posts:
        return
        
    # 论坛ID到名称的映射
    forum_map = {'52': '候车室', '61': '攻略区'}
        
    for post in posts:
        # 转换forum_id为中文名称
        forum_id = str(post['forum_id'])
        forum_name = forum_map.get(forum_id, forum_id)
        
        # 发送钉钉通知
        from dingtalk_notify import notify_new_post
        notify_new_post(post['post'])
        
        # 发送企业微信通知
        from wechat_notify import notify_new_post
        notify_new_post(post['post'])
        
        post_data = {
            'post_id': post['post']['post_id'],
            'forum_id': forum_name,
            'title': post['post']['subject'],
            'content': post['post']['content'],
            'keywords': '、'.join(post['matched_keywords']),
            'url': f"https://www.miyoushe.com/sr/article/{post['post']['post_id']}",
            'author': post['post'].get('user', {}).get('nickname', '匿名用户'),
            'author_id': post['post'].get('user', {}).get('uid', ''),
            'created_at': post['post']['created_at'],
            'updated_at': post['post']['updated_at'],
            'view_count': post['post'].get('view_count', 0),
            'reply_count': post['post'].get('reply_count', 0),
            'like_count': post['post'].get('like_count', 0)
        }
        
        # 先检查帖子是否已存在
        if DB.post_exists(post_data['post_id']):
            DB.delete_post(post_data['post_id'])
            logging.info(f"已删除旧帖子: {post_data['post_id']}")
            
            # 发送更新通知
            from dingtalk_notify import notify_new_post
            notify_new_post(post['post'], is_update=True)
            
            # 发送企业微信更新通知
            from wechat_notify import notify_new_post
            notify_new_post(post['post'], is_update=True)
            
        DB.save_post(post_data)
        
    logging.info(f"成功保存{len(posts)}条帖子数据到数据库")

# 添加重试次数和间隔时间配置
MAX_RETRIES = 5  # 最大重试次数
RETRY_DELAY = 30  # 固定重试延迟（秒）

def retry_get_posts(forum_id, retries=MAX_RETRIES):
    """使用固定30秒间隔的重试机制获取帖子，区分连接失败和没有匹配关键词的帖子的情况"""
    all_results = []
    
    # 同时获取最新回复和最新发布的帖子
    for sort_type in [1, 2]:  # 1=最新回复, 2=最新发布
        for attempt in range(retries):
            # 获取帖子数据
            result = get_posts(forum_id, sort_type)
            
            # 检查返回结果
            # 如果result为None，表示连接失败或数据结构异常，需要重试
            # 如果result是空列表，表示成功获取数据但没有匹配的帖子，不需要重试
            # 如果result有内容，表示成功获取到匹配的帖子，不需要重试
            
            # 如果成功获取到数据（无论是否有匹配的帖子）
            if result is not None:
                # 如果有匹配的帖子，添加到结果列表
                if result:
                    all_results.extend(result)
                    logging.info(f"第{attempt+1}次尝试成功获取到 {len(result)} 个匹配关键词的帖子")
                else:
                    # 成功获取数据但没有匹配的帖子
                    logging.info(f"第{attempt+1}次尝试成功获取数据，但没有找到匹配关键词的帖子")
                
                # 继续尝试另一种排序方式
                break
            
            # 连接失败或数据结构异常，需要重试
            # 如果是最后一次尝试，返回所有已收集的结果
            if attempt == retries - 1:
                logging.warning(f"已达到最大重试次数 {retries}，返回已收集的 {len(all_results)} 个结果")
                return all_results
                
            # 使用固定的30秒延迟时间
            logging.warning(f"第{attempt+1}次尝试获取数据失败，{RETRY_DELAY}秒后重试...")
            time.sleep(RETRY_DELAY)
    
    # 如果所有尝试都失败但收集到了一些结果，仍然返回这些结果
    if all_results:
        logging.info(f"成功收集到 {len(all_results)} 个匹配的帖子")
    
    return all_results

def main():
    try:
        while True:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"开始检查新帖子...")
            
            # 首先检查网络连接
            if not check_internet_connection():
                logging.warning("网络连接不可用，但仍将尝试获取数据...")
                # 不再直接跳过，而是继续尝试，因为即使网络不稳定也可能获取到部分数据
                
            for forum_id in forum_ids:
                forum_name = "候车室" if forum_id == 52 else "攻略" if forum_id == 61 else f"未知论坛({forum_id})"
                logging.info(f"正在检查论坛: {forum_name}...")
                
                # 使用改进的重试函数获取帖子
                hitted_post = retry_get_posts(forum_id)
                
                if len(hitted_post) > 0:
                    logging.info(f"发现 {len(hitted_post)} 个匹配关键词的帖子!")
                    content = ""
                    for post in hitted_post:
                        # 提取帖子信息
                        post_id = post['post']['post_id']
                        subject = post['post']['subject']
                        # 只在日志中显示摘要，避免日志过大
                        content_text = post['post']['content']
                        if len(content_text) > 100:
                            content_summary = content_text[:100] + "..."
                        else:
                            content_summary = content_text
                            
                        content += f"论坛: {forum_name}\n标题: {subject}\n内容摘要: {content_summary}\n链接: https://www.miyoushe.com/sr/article/{post_id}\n\n"
                    
                    # 记录摘要信息到日志
                    logging.info(f"匹配帖子摘要:\n{content}")
                    
                    # 为每个帖子添加forum_id信息并保存到数据库
                    for post in hitted_post:
                        post['forum_id'] = forum_id
                        post['matched_keywords'] = [kw for kw in keywords if kw in post['post']['subject'] or kw in post['post']['content']]
                    save_to_database(hitted_post)
                else:
                    logging.info(f"未发现匹配关键词的新帖子")
            
            logging.info(f"休眠30秒后继续检查...")
            time.sleep(30)
    except KeyboardInterrupt:
        logging.info("程序被用户中断，正在退出...")
    except Exception as e:
        logging.error(f"程序发生未预期的错误: {e}")
        # 记录详细的异常信息以便调试
        import traceback
        logging.error(f"异常详情: {traceback.format_exc()}")
        raise

# 启动主程序
if __name__ == "__main__":
    main()