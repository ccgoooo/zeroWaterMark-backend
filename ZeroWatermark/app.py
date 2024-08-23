from flask import Flask, render_template, request, json, redirect, flash, jsonify, url_for  # 导入Flask库
import pymysql
import os
from flask_cors import CORS
from werkzeug.utils import secure_filename
import watermark
import greyscaleImage
from dashboard_routes import dashboard_bp
from flask_jwt_extended import JWTManager
from logs import logs_bp
from user_manage import user_manage_bp
from datetime import datetime, timezone, timedelta
from decorators import validate_jwt, check_permissions
import comparison
from creat_log import create_logger

app = Flask(__name__)  # 创建一个Flask应用实例，__name__代表当前模块的名称
CORS(app)  # 启用CORS，允许所有域名访问
logger = create_logger(app)

# 配置密钥和JWT过期时间
app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # 替换为强密钥
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)  # JWT过期时间

# 初始化JWT管理
jwt = JWTManager(app)

# 注册蓝图
app.register_blueprint(user_manage_bp, url_prefix='/user_manage')
# app.register_blueprint(user_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(logs_bp)

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

# 请求前日志记录
@app.before_request
def log_request_on_before_request():
    app.logger.info(f"Request started for {request.remote_addr} to {request.url}")

# 请求后日志记录
@app.after_request
def log_request_on_after_request(response):
    app.logger.info(f"Request completed for {request.remote_addr} to {request.url} with status {response.status_code}")
    return response

@app.route("/gen_new_wm", methods=['GET', 'POST'])
@validate_jwt
def gen_new_wm():  # 先从前端获取数据（文件），进行生成操作后，存储水印至数据库，并返回结果给前端
    # 连接数据库
    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()

    # 检查请求是否是post类型
    if request.method == 'POST':

        # 获取生成时间、用户角色、用户id、用户名字、用户ip、渠道
        gentime = request.form.get('gentime')
        role = request.form.get('userrole')
        userId = request.form.get('userid')
        userName = request.form.get('username')
        userIP = request.form.get('userip')
        channel = '国家电网'

        # 初始化文件路径的列表
        filepath = []
        # 检查是否有文件列表被上传
        if 'fileList' in request.files:
            # 获取文件列表中的所有文件
            file_list = request.files.getlist('fileList')
            for idx, file in enumerate(file_list):
                if file:
                    # 将文件存储在本地路径上
                    file_path = os.path.join(r'F:\用户\Desktop\test', file.filename)
                    filepath.append(file_path)
                    file.save(file_path)

            # 处理接收到的数据，可以在这里添加进一步的处理逻辑
            for file_p, file in zip(filepath, file_list):
                # 截断到45个字符
                feature = watermark.extraction(file_p)
                if len(feature) > 45:
                    feature = feature[:45] + "..."
                result = watermark.watermark(file_p, gentime, role, userId, userName, userIP, channel)
                print(result)

                # 写入数据库：数据特征、水印信息（多种）、零水印
                sql = "INSERT INTO information(feature,mark,filename,gen_time,role,user_id,user_name,user_ip,channel) " \
                      "VALUES('%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
                      % (feature, result, file.filename, gentime, role, userId, userName, userIP, channel)
                cur.execute(sql)
                db.commit()

    cur.close()
    db.close()

    return 'file has been delivered!', 200


@app.route('/get_gen_list', methods=['POST'])
@validate_jwt
def get_gen_list():
    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()

    res_data = {
        "code": 200,
        "data": {
            "items": []
        }
    }

    sql_count = "SELECT COUNT(*) FROM information"
    cur.execute(sql_count)
    total_rows = cur.fetchone()[0]
    # 若数据库数据不足，则只展示仅有的数据，否则最多展示20条
    if total_rows > 20:
        total_rows = 20

    sql = "SELECT * FROM information ORDER BY id DESC LIMIT %s"
    cur.execute(sql, (total_rows,))
    # 获取所有查询结果
    results = cur.fetchall()
    if results:
        for result in results:
            info = {}
            info['id'] = result[3]
            info['filename'] = result[2]
            info['zerowm'] = greyscaleImage.hex_to_32x32_binary_image(result[1])
            info['gentime'] = result[4]
            info['userrole'] = result[5]
            info['userid'] = result[6]
            info['username'] = result[7]
            info['userip'] = result[8]
            res_data['data']['items'].append(info)

    cur.close()
    db.close()

    return jsonify(res_data), 200


@app.route("/rec_new_wm", methods=['GET', 'POST'])
@validate_jwt
def rec_new_wm():  # 从前端获取数据，进行相关操作，从数据库中搜索，返回结果至前端
    # 连接数据库
    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()
    dict2 = {}
    res_data = {
        "code": 200,
        "data": {
            "items": []
        }
    }

    # 检查请求是否包含multipart/form-data类型
    if request.method == 'POST':
        # 用户角色、用户id、用户名字、用户ip、渠道（时间不需要匹配）
        dict2['role'] = request.form.get('userrole')
        dict2['user_id'] = request.form.get('userid')
        dict2['user_name'] = request.form.get('username')
        dict2['user_ip'] = request.form.get('userip')
        dict2['channel'] = '国家电网'
        gentime = request.form.get('gentime')

        # 初始化文件路径的列表
        filepath = []

        # 检查是否有文件列表被上传
        if 'fileList' in request.files:
            # 获取文件列表中的所有文件
            file_list = request.files.getlist('fileList')
            for idx, file in enumerate(file_list):
                if file:
                    # 将文件存储在本地路径上
                    file_path = os.path.join(r'F:\用户\Desktop\test\re', file.filename)
                    filepath.append(file_path)
                    file.save(file_path)

            # 处理接收到的数据，可以在这里添加进一步的处理逻辑
            column_names = ["mark", "role", "user_id", "user_name", "user_ip", "channel"]
            for file_p, file in zip(filepath, file_list):
                feature = watermark.extraction(file_p)
                dict2["mark"] = watermark.watermark(file_p, gentime, dict2['role'],dict2['user_id'], dict2['user_name'], dict2['user_ip'], dict2['channel'])
                dict2["filename"] = file.filename

                if len(feature) > 45:
                    feature = feature[:45] + "..."
                search_value = feature
                search_sql = "SELECT mark,role,user_id,user_name,user_ip,channel FROM information WHERE feature LIKE %s"
                cur.execute(search_sql, (search_value,))
                result_1 = cur.fetchone()
                if result_1 :
                    # 获取查询结果的第一行
                    dict2["result"] = 0
                    dict1 = dict(zip(column_names, result_1))
                    # 比对是否有所不同
                    different_keys = []
                    for key in column_names:
                        if dict1[key] != dict2[key]:
                            different_keys.append(key)
                    if different_keys:
                        dict2["resultMsg"] = "存在异动"
                    else:
                        dict2["resultMsg"] = "未有异动"
                else:
                    print("溯源失败")
                    dict2["result"] = 1
                    dict2["resultMsg"] = "溯源失败"

                sql_1 = "INSERT INTO rec_history(flag,mark,feature,filename,err_info,gen_time,role,user_id,user_name,user_ip,channel) " \
                        "VALUES('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" % \
                        (dict2['result'], dict2['mark'], feature, dict2['filename'], dict2['resultMsg'], gentime,
                         dict2['role'], dict2['user_id'], dict2['user_name'], dict2['user_ip'], dict2['channel'])
                cur.execute(sql_1)
                db.commit()

    cur.close()
    db.close()

    return jsonify(res_data), 200


@app.route('/get_rec_list', methods=['POST'])
@validate_jwt
def get_rec_list():
    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()

    res_data = {
        "code": 200,
        "data": {
            "items": []
        }
    }

    sql_count = "SELECT COUNT(*) FROM rec_history"
    cur.execute(sql_count)
    total_rows = cur.fetchone()[0]
    # 若数据库数据不足，则只展示仅有的数据，否则最多展示20条
    if total_rows > 20:
        total = 20
    else:
        total = total_rows

    sql = "SELECT * FROM rec_history ORDER BY id DESC LIMIT %s"
    cur.execute(sql, (total,))
    # 获取所有查询结果
    results = cur.fetchall()
    if results:
        acc_num = 0
        for result in results:
            info = {}
            info['result'] = result[0]
            info['filename'] = result[3]
            info['id'] = result[4]
            info['datafeat'] = result[2]
            info['zerowm'] = greyscaleImage.hex_to_32x32_binary_image(result[1])
            info['resultMsg'] = result[5]
            info['gentime'] = result[6]
            info['userrole'] = result[7]
            info['userid'] = result[8]
            info['username'] = result[9]
            info['userip'] = result[10]
            if info['result'] == 0:
                acc_num += 1

            res_data['data']['items'].append(info)
        if total_rows != 0:
            res_data['data']['acc'] = round(acc_num / total_rows, 2) * 100
            print(res_data['data']['acc'])

    cur.close()
    db.close()
    return jsonify(res_data), 200


# 根据溯源Id获取对比信息
@app.route('/get_cmp_info', methods=['POST'])
@validate_jwt
def get_cmp_info():
    # 获取前端发送的FormData数据
    id = request.form.get('cmpId')

    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()
    cur.execute("select err_info,feature from rec_history where id = %s", (id,))
    result = cur.fetchone()
    if result[0] == "溯源失败":
        mock_data = {
            "code": 200,
            "data": {
                "comparsionData": [
                    {
                        "field": "文档特征",
                        "value1": result[1],
                        "value2": "未找到",
                        "comparisonCode": 0,
                        "isPicture": 0,
                        "comparisonReason": "特征不匹配"
                    }
                ]
            }
        }
        # 此时数据库没有对应数据
        print("get_cmp_info,文档匹配失败")
        return jsonify(mock_data), 200


    sql = "SELECT  feature,mark,gen_time,role,user_id,user_name,user_ip,channel FROM rec_history WHERE id = %s"
    cur.execute(sql, (id,))
    result_2 = cur.fetchone()
    column_names = ["特征","零水印","生成时间","用户角色","用户ID","用户名","用户IP","所属机构"]
    dict2 = dict(zip(column_names, result_2))

    # 根据文件名取出水印数据库中相关对应数据
    sql = "SELECT feature,mark,gen_time,role,user_id,user_name,user_ip,channel FROM information WHERE feature = %s"
    cur.execute(sql, (result_2[0],))
    result_1 = cur.fetchone()

    dict1 = dict(zip(column_names, result_1))
    # 信息比较
    mock_data = comparison.comparisonInfomation(dict1, dict2, column_names)
    cur.close()
    db.close()

    return jsonify(mock_data), 200


# 根据溯源Id删除记录
@app.route('/delete_rec_record', methods=['POST'])
@validate_jwt
@check_permissions('admin')
def delete_rec_record():
    # 获取前端发送的FormData数据
    data = request.form

    # 将FormData数据转换为字典
    received_data = {key: data[key] for key in data.keys()}

    print(f"Received data: {received_data}")

    # 实际上是数据库里删掉对应记录
    del_id= received_data['cmpId']
    db = pymysql.connect(host=HOSTNAME, port=PORT, user=USERNAME, passwd=PASSWORD, db=DATABASE)
    cur = db.cursor()
    sql = "DELETE FROM rec_history WHERE id = %s"
    cur.execute(sql, (del_id,))
    db.commit()
    cur.close()
    db.close()
    response = {
        'message': 'Data delete successfully',
        # 'received_data': received_data
    }
    return jsonify(response), 200


if __name__ == '__main__':  # 检查当前模块是否作为主程序运行
    app.run(debug=True)  # 启动Flask的开发服务器，监听请求并响应，默认运行在http://127.0.0.1:5000/
