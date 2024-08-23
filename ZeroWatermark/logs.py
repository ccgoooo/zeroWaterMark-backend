from flask import Flask,Blueprint, jsonify,request
from decorators import validate_jwt, check_permissions  # 导入装饰器
import os
from creat_log import create_logger
from datetime import datetime

# 创建一个Flask蓝图
logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/get_logs', methods=['GET'])
@validate_jwt
@check_permissions('admin')
def get_logs():
    # 读取日志文件
    try:
        with open('app.log', 'r') as file:
            log_entries = file.readlines()
    except FileNotFoundError:
        log_entries = ["Log file does not exist or has been moved."]

    # 格式化日志数据
    logs = [{"timestamp": entry.split(" - ")[0], "level": entry.split(" - ")[1], "message": entry.split(" - ")[2]} for
            entry in log_entries]

    # 返回日志数据
    return jsonify({"code": 200, "data": {"logs": logs}})