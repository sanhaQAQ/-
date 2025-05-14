import sys
import os
import pandas as pd
import configparser
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel,
                             QHBoxLayout, QHeaderView, QComboBox, QFileDialog, QDateEdit, QDialog, QListWidget)
from PyQt6.QtCore import Qt, QUrl, QDate
from PyQt6.QtGui import QDesktopServices, QPalette, QColor, QFont, QIcon
from datetime import datetime
import webbrowser

class SRDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('星穹铁道 - 帖子数据查看器')
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1b2e;
            }
            QTableWidget {
                background-color: #252640;
                color: #ffffff;
                border: 1px solid #3d3e5c;
                gridline-color: #3d3e5c;
                font-family: "Microsoft YaHei";
            }
            QTableWidget::item:selected {
                background-color: #3d3e5c;
            }
            QHeaderView::section {
                background-color: #2d2e4a;
                color: #ffffff;
                border: 1px solid #3d3e5c;
                padding: 4px;
                font-family: "Microsoft YaHei";
            }
            QPushButton {
                background-color: #3d3e5c;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-family: "Microsoft YaHei";
            }
            QPushButton:hover {
                background-color: #4d4e6c;
            }
            QLineEdit, QComboBox {
                background-color: #252640;
                color: #ffffff;
                border: 1px solid #3d3e5c;
                padding: 4px;
                border-radius: 4px;
                font-family: "Microsoft YaHei";
            }
            QLabel {
                color: #ffffff;
                font-family: "Microsoft YaHei";
            }
        """)
        
        # 设置窗口大小
        self.setMinimumSize(1200, 800)
        
        # 创建主窗口部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建过滤布局
        filter_layout = QHBoxLayout()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索...')
        filter_layout.addWidget(self.search_input)
        
        # 论坛筛选
        self.forum_filter = QComboBox()
        self.forum_filter.addItem('全部论坛')
        filter_layout.addWidget(self.forum_filter)
        
        # 关键词管理按钮
        self.keyword_btn = QPushButton('关键词管理')
        self.keyword_btn.clicked.connect(self.show_keyword_dialog)
        filter_layout.addWidget(self.keyword_btn)
        
        # 导入按钮
        import_btn = QPushButton('导入数据')
        import_btn.clicked.connect(self.import_data)
        filter_layout.addWidget(import_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton('刷新数据')
        refresh_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(refresh_btn)
        
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(['唯一ID', '时间戳', '分区', '帖子ID', '标题', '内容摘要', '匹配关键词', '链接'])
        
        # 设置表格列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        # 添加布局
        layout.addLayout(filter_layout)
        layout.addWidget(self.table)
        
        # 加载数据
        self.load_data()
        
        # 连接单元格点击事件
        self.table.cellClicked.connect(self.handle_cell_click)
    
    def load_data(self):
        # 检查并导出数据库
        db_path = 'posts.db'
        excel_dir = 'excel'
        
        if os.path.exists(db_path):
            try:
                import sqlite3
                from datetime import datetime
                
                # 创建excel目录
                os.makedirs(excel_dir, exist_ok=True)
                
                # 连接数据库
                conn = sqlite3.connect(db_path)
                df = pd.read_sql('SELECT id, timestamp, forum_id, post_id, title, content, keywords, url FROM posts', conn)
                conn.close()
                
                # 导出Excel
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                excel_path = os.path.join(excel_dir, f'posts_{timestamp}.xlsx')
                df.to_excel(excel_path, index=False)
                
            except Exception as e:
                print(f'数据库导出失败: {e}')
        
        # 获取excel文件夹中最新的文件
        if not os.path.exists(excel_dir):
            return
            
        excel_files = [f for f in os.listdir(excel_dir) if f.endswith('.xlsx')]
        if not excel_files:
            return
        
        latest_file = max(excel_files, key=lambda x: os.path.getmtime(os.path.join(excel_dir, x)))
        file_path = os.path.join(excel_dir, latest_file)
        
        try:
            # 读取Excel文件
            self.df = pd.read_excel(file_path)
            self.filter_data()
        except Exception as e:
            print(f'加载数据失败: {e}')
    
    def filter_data(self):
        if not hasattr(self, 'df'):
            return
        
        # 获取过滤条件
        search_text = self.search_input.text().lower()
        forum_filter = self.forum_filter.currentText()
        
        # 应用过滤
        filtered_df = self.df.copy()
        # 论坛ID到名称的映射
        forum_map = {'52': '候车室', '61': '攻略'}
        
        if forum_filter != '全部论坛':
            # 将论坛名称转换回ID进行过滤
            forum_id = next((k for k, v in forum_map.items() if v == forum_filter), forum_filter)
            filtered_df = filtered_df[filtered_df['分区'] == forum_id]
            
            # 将论坛ID转换为名称显示
            filtered_df['分区'] = filtered_df['分区'].replace(forum_map)
        
        if search_text:
            mask = filtered_df['标题'].str.lower().str.contains(search_text, na=False) |\
                   filtered_df['内容摘要'].str.lower().str.contains(search_text, na=False) |\
                   filtered_df['匹配关键词'].str.lower().str.contains(search_text, na=False)
            filtered_df = filtered_df[mask]
        
        # 更新表格
        self.table.setRowCount(len(filtered_df))
        for i, row in filtered_df.iterrows():
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                if j == 7:  # 链接列
                    item.setForeground(QColor('#4a9eff'))
                self.table.setItem(i, j, item)
    
    def handle_cell_click(self, row, col):
        if col == 7:  # 链接列
            url = self.table.item(row, col).text()
            QDesktopServices.openUrl(QUrl(url))
            
    def show_keyword_dialog(self):
        """显示关键词管理对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle('关键词管理')
        dialog.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # 关键词列表
        self.keyword_list = QListWidget()
        self.load_keywords()
        layout.addWidget(self.keyword_list)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        
        # 添加关键词
        self.new_keyword_input = QLineEdit()
        self.new_keyword_input.setPlaceholderText('输入新关键词')
        btn_layout.addWidget(self.new_keyword_input)
        
        add_btn = QPushButton('添加')
        add_btn.clicked.connect(self.add_keyword)
        btn_layout.addWidget(add_btn)
        
        # 删除关键词
        del_btn = QPushButton('删除')
        del_btn.clicked.connect(self.delete_keyword)
        btn_layout.addWidget(del_btn)
        
        layout.addLayout(btn_layout)
        
        # 保存按钮
        save_btn = QPushButton('保存')
        save_btn.clicked.connect(lambda: self.save_keywords(dialog))
        layout.addWidget(save_btn)
        
        dialog.exec()
    
    def load_keywords(self):
        """从配置文件加载关键词"""
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')
        keywords = config['keywords']['keywords'].split(',')
        
        self.keyword_list.clear()
        for keyword in keywords:
            self.keyword_list.addItem(keyword.strip())
    
    def add_keyword(self):
        """添加新关键词"""
        keyword = self.new_keyword_input.text().strip()
        if keyword and not self.keyword_list.findItems(keyword, Qt.MatchFlag.MatchExactly):
            self.keyword_list.addItem(keyword)
            self.new_keyword_input.clear()
    
    def delete_keyword(self):
        """删除选中的关键词"""
        selected = self.keyword_list.currentItem()
        if selected:
            self.keyword_list.takeItem(self.keyword_list.row(selected))
    
    def save_keywords(self, dialog):
        """保存关键词到配置文件"""
        keywords = []
        for i in range(self.keyword_list.count()):
            keywords.append(self.keyword_list.item(i).text())
        
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')
        config['keywords']['keywords'] = ','.join(keywords)
        
        with open('config.ini', 'w', encoding='utf-8') as f:
            config.write(f)
        
        dialog.close()
        
    def import_data(self):
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Excel文件",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            try:
                # 读取Excel文件
                self.df = pd.read_excel(file_path)
                self.filter_data()
            except Exception as e:
                print(f'导入数据失败: {e}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序范围的字体
    app.setFont(QFont('Arial', 9))
    
    window = SRDataViewer()
    window.show()
    sys.exit(app.exec())