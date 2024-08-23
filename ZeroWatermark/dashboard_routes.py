from flask import Blueprint, jsonify
from decorators import validate_jwt,check_permissions  # 导入装饰器
import pymysql
from collections import defaultdict
from datetime import datetime
# 定义蓝图
dashboard_bp = Blueprint('dashboard', __name__)

# MySQL所在主机名
HOSTNAME = "127.0.0.1"
# MySQL监听的端口号，默认3306
PORT = 3306
# 连接MySQL的用户名，自己设置
USERNAME = "root"
# 连接MySQL的密码，自己设置
PASSWORD = "160336"
# MySQL上创建的数据库名称
DATABASE = "database_ZWM"
# 连接数据库
db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
cur = db.cursor()
# 定义接口
@dashboard_bp.route('/get_dashboard_info', methods=['GET'])
@validate_jwt
def get_dashboard_info():


    # 查询并统计信息
    zwm_date_counts, zwm_num = fetch_and_count('information')
    rec_date_counts, rec_num = fetch_and_count('rec_history')

    # 关闭游标和数据库连接
    cur.close()
    db.close()

    # 确保两个字典都有相同的键名，缺失的键名赋予值为0
    all_dates = set(zwm_date_counts.keys()) | set(rec_date_counts.keys())
    for date in all_dates:
        zwm_date_counts.setdefault(date, 0)
        rec_date_counts.setdefault(date, 0)

    # 提取键名和键值列表
    date_keys = list(all_dates)
    rec_values = list(rec_date_counts.values())
    zwm_values = list(zwm_date_counts.values())

    # 构建响应数据
    response_data = {
        "code": 200,
        "data": {
            "panelData": {
                "user_num": 303,
                "gen_wm_num": zwm_num,
                "rec_wm_num": rec_num,
                "rec_acc": ' '
            },
            "lineChartData": {
                "genWMCount": zwm_values,
                "recWMCount": rec_values,
                "dataXaxis":date_keys
            }
        }
    }
    # 返回JSON响应
    return jsonify(response_data)

# 执行查询并存储结果的函数
def fetch_and_count(table_name):
    sql = f"SELECT gen_time FROM {table_name};"
    cur.execute(sql)
    dates = cur.fetchall()
    num = cur.rowcount
    date_counts = defaultdict(int)
    for date_tuple in dates:
        date_str = date_tuple[0]
        # 分析字符串
        formatted_date = date_str.split(' ')[0].split('-')[1] + '-' + date_str.split(' ')[0].split('-')[2]
        date_counts[formatted_date] += 1
    return date_counts, num
