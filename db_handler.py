import sqlite3
import os
from datetime import datetime
import logging

class DBHandler:
    def __init__(self, db_path='posts.db'):
        """初始化数据库连接"""
        self.db_path = db_path
        self.conn = None
        self._init_db()
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("db_handler.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def _init_db(self):
        """初始化数据库表结构"""
        self._connect()
        cursor = self.conn.cursor()
        
        # 删除旧表（如果存在）
        cursor.execute('DROP TABLE IF EXISTS posts')
        
        # 创建新帖子表
        cursor.execute('''
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL UNIQUE,
            forum_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            keywords TEXT,
            url TEXT,
            author TEXT,
            author_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            view_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建关键词表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            count INTEGER DEFAULT 1
        )
        ''')
        
        self.conn.commit()
        
    def _connect(self):
        """建立数据库连接"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
    
    def save_post(self, post_data):
        """保存帖子数据到数据库"""
        try:
            self._connect()
            cursor = self.conn.cursor()
            
            # 插入或更新帖子数据
            cursor.execute('''
            INSERT OR REPLACE INTO posts 
            (post_id, forum_id, title, content, keywords, url, timestamp,
             author, author_id, created_at, updated_at, view_count, reply_count, like_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data['post_id'],
                post_data['forum_id'],
                post_data['title'],
                post_data['content'],
                post_data['keywords'],
                post_data['url'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                post_data.get('author', ''),
                post_data.get('author_id', ''),
                post_data.get('created_at', ''),
                post_data.get('updated_at', ''),
                post_data.get('view_count', 0),
                post_data.get('reply_count', 0),
                post_data.get('like_count', 0)
            ))
            
            # 更新关键词统计
            if post_data['keywords']:
                keywords = post_data['keywords'].split('、')
                for keyword in keywords:
                    cursor.execute('''
                    INSERT OR IGNORE INTO keywords (keyword) VALUES (?)
                    ''', (keyword,))
                    cursor.execute('''
                    UPDATE keywords SET count = count + 1 WHERE keyword = ?
                    ''', (keyword,))
            
            self.conn.commit()
            logging.info(f"成功保存帖子: {post_data['post_id']}")
            return True
        except Exception as e:
            logging.error(f"保存帖子失败: {e}")
            return False
    
    def get_posts(self, filters=None):
        """根据条件查询帖子数据"""
        try:
            self._connect()
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM posts"
            params = []
            
            if filters:
                conditions = []
                
                if 'forum_id' in filters:
                    conditions.append("forum_id = ?")
                    params.append(filters['forum_id'])
                
                if 'keywords' in filters:
                    keyword_conditions = []
                    for keyword in filters['keywords']:
                        keyword_conditions.append("keywords LIKE ?")
                        params.append(f"%{keyword}%")
                    conditions.append(f"({' OR '.join(keyword_conditions)})")
                
                if 'start_date' in filters and 'end_date' in filters:
                    conditions.append("timestamp BETWEEN ? AND ?")
                    params.extend([filters['start_date'], filters['end_date']])
                
                if 'search_text' in filters:
                    conditions.append("(title LIKE ? OR content LIKE ?)")
                    params.extend([f"%{filters['search_text']}%", f"%{filters['search_text']}%"]) 
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC"
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results
        except Exception as e:
            logging.error(f"查询帖子失败: {e}")
            return []
    
    def get_keywords(self):
        """获取所有关键词及其出现次数"""
        try:
            self._connect()
            cursor = self.conn.cursor()
            
            cursor.execute("SELECT keyword, count FROM keywords ORDER BY count DESC")
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"获取关键词失败: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def post_exists(self, post_id):
        """检查帖子是否已存在"""
        try:
            self._connect()
            cursor = self.conn.cursor()
            cursor.execute('SELECT 1 FROM posts WHERE post_id = ?', (post_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            logging.error(f"检查帖子存在性失败: {e}")
            return False
            
    def __del__(self):
        """析构函数自动关闭连接"""
        self.close()