from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request
from datetime import datetime, timezone
import pymysql

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

# JWT验证装饰器
def validate_jwt(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()

            jwt_data = get_jwt()
            username = get_jwt_identity()

            # 从数据库模拟的数据中获取用户信息
            db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
            cur = db.cursor()
            sql = "select * from login where username = %s"
            cur.execute(sql, (username,))
            # 检查用户是否一致
            if cur.rowcount < 0:
                return jsonify({"code": 401, "msg": "Invalid user, please login again"})

            # 检查JWT是否与数据库中的一致
            result = cur.fetchone()
            cur.close()
            db.close()
            if result[4] != request.headers.get('Authorization').split(" ")[1]:
                return jsonify({"code": 401, "msg": "JWT mismatch, please login again"})

            # 检查UA是否匹配
            user_agent = request.headers.get('User-Agent')
            if jwt_data["user_agent"] != user_agent:
                return jsonify({"code": 401, "msg": "User-Agent mismatch, please login again"})

            # 检查JWT是否过期
            exp_timestamp = jwt_data['exp']
            now = datetime.now(timezone.utc)
            if datetime.fromtimestamp(exp_timestamp, timezone.utc) < now:
                return jsonify({"code": 401, "msg": "Token expired, please login again"})

        except Exception as e:
            return jsonify({"code": 401, "msg": str(e)})

        return func(*args, **kwargs)
    return wrapper

# 权限校验装饰器
def check_permissions(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            username = get_jwt_identity()
            db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
            cur = db.cursor()
            sql = "select * from login where username = %s"
            cur.execute(sql, (username,))
            result = cur.fetchone()
            cur.close()
            db.close()
            if not result or result[3] != required_role:
                return jsonify({"code": 403, "msg": "权限控制: 非法访问"})
            return func(*args, **kwargs)
        return wrapper
    return decorator
