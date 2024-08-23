from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token,jwt_required,get_jwt_identity,get_jwt
from decorators import validate_jwt, check_permissions  # 导入装饰器
from datetime import timedelta
import base58
import pymysql

# 创建蓝图
user_manage_bp = Blueprint('user_manage', __name__)
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


# 登录路由，生成JWT
@user_manage_bp.route('/login', methods=['POST'])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    print('login received', username, password)
    # 对密码解码
    password = base58.b58decode(password).decode('utf-8')
    user_agent = request.headers.get('User-Agent')

    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()
    sql = "SELECT * FROM login WHERE username = %s"
    cur.execute(sql, (username,))
    if cur.rowcount > 0:
        result = cur.fetchone()
        print(result)
        if result[2] != password:
            return jsonify({"msg": "登录失败，账号或密码错误"}), 401
    else:
        return jsonify({"msg": "登录失败，账号或密码错误"}), 401

    # 构建JWT的额外数据
    additional_claims = {
        "userid": result[0],
        "userrole": result[3],
        "user_agent": user_agent,  # 浏览器信息
    }

    # 创建JWT并保存到模拟数据库中
    access_token = create_access_token(identity=username, additional_claims=additional_claims)
    sql = f"UPDATE login SET jwt = %s WHERE username = %s"
    cur.execute(sql, (access_token, username))
    # 提交事务
    db.commit()
    cur.close()
    db.close()

    return jsonify({
        "jwt": access_token,
        "user_info": {
            "username": username,
            "userid": additional_claims["userid"],
            "userrole": additional_claims["userrole"]
        }
    })


# 注册路由，创建用户并生成JWT
@user_manage_bp.route('/register', methods=['POST'])
def register():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    password = base58.b58decode(password).decode('utf-8')
    userrole = request.json.get("userrole", "user")  # 默认为普通用户角色
    user_agent = request.headers.get('User-Agent')

    # 验证请求数据
    if not username or not password:
        return jsonify({"msg": "用户名和密码是必填项"}), 400

    # 检查用户名是否已存在
    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()
    sql = "select * from login where username = %s"
    cur.execute(sql, (username,))
    if cur.rowcount > 0:
        return jsonify({"msg": "用户名已存在"}), 400

    # 构建JWT的额外数据
    row_count_sql = "SELECT COUNT(*) FROM login"
    cur.execute(row_count_sql)
    row_count_result = cur.fetchone()
    id = row_count_result[0]
    additional_claims = {
        "userid": id+1,
        "userrole": userrole,
        "user_agent": user_agent,  # 浏览器信息
    }

    # 创建JWT并保存到模拟数据库中
    access_token = create_access_token(identity=username, additional_claims=additional_claims)
    print(access_token)
    sql = "INSERT INTO login(username,password,role,jwt) VALUES('%s','%s','%s','%s')" % (username, password,userrole,access_token)
    cur.execute(sql)
    db.commit()
    cur.close()
    db.close()

    # 返回用户信息和JWT
    return jsonify({
        "jwt": access_token,
        "user_info": {
            "username": username,
            "userid": id+1,
            "userrole": userrole
        }
    })


@user_manage_bp.route('/logout', methods=['POST'])
def logout():
    # 从请求体中获取用户名
    username = request.json.get("username", None)

    # 检查是否提供了用户名
    if not username:
        return jsonify({"code": 200, "msg": "Username is required"}), 200

    # 清除用户的JWT
    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()
    sql = "UPDATE login SET jwt = NULL WHERE username = %s;"
    cur.execute(sql, (username,))
    db.commit()

    return jsonify({"code": 200, "msg": "Logout successful"}), 200

# # 受保护的路由，需要JWT认证并校验权限
# @user_manage_bp.route('/admin', methods=['GET'])
# @validate_jwt
# @check_permissions('admin')
# def admin_only():
#     return jsonify(msg="Welcome, admin!"), 200
