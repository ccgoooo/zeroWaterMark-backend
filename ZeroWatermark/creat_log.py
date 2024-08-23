import logging

class CustomLogFilter(logging.Filter):
    def filter(self, record):
        # 根据需要自定义过滤逻辑
        # 例如，只记录包含特定关键字的日志
        return '特定关键字' in record.getMessage()

def create_logger(app):
    # 创建一个日志器
    logger = logging.getLogger(app.logger.name)
    logger.setLevel(logging.DEBUG)  # 设置最低捕获级别为DEBUG

    # 创建一个控制台handler，用于输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 设置控制台输出的日志级别为WARNING

    # 创建一个文件handler，用于写入日志文件
    file_handler = logging.FileHandler('app.log')
    file_handler.setLevel(logging.DEBUG)  # 设置文件记录的日志级别为DEBUG

    # 创建日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 设置日志格式
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 添加过滤器
    file_handler.addFilter(CustomLogFilter())

    # 将handler添加到logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger