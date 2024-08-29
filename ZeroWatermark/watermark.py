import hashlib
import os
import re
import jieba.analyse
from docx import Document
import pandas as pd
import ast
import time
import numpy as np
from collections import Counter

# 停用词路径（可以是一个有效的停用词列表路径，如果没有，可以注释掉）
STOPWORDS_PATH = 'stop_words.txt'

# 自定义短语词典路径
PHRASES_PATH = 'rake_words.txt'

# 局部敏感哈希算法
class PerceptualHash:
    def __init__(self, hash_size=64):
        self.hash_size = hash_size

    def _normalize_text(self, text):
        """标准化文本，去除多余的符号和空格，统一大小写。"""
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)  # 将多个空格替换为一个空格
        text = re.sub(r'[^\w\s]', '', text)  # 移除标点符号
        return text.strip()

    def _get_features(self, text):
        """获取文本的特征及其权重，这里简单处理为按词频。"""
        tokens = text.split()  # 简单分词
        return Counter(tokens)

    def compute(self, text):
        """计算文本的感知哈希值。"""
        text = self._normalize_text(text)
        features = self._get_features(text)
        v = np.zeros(self.hash_size)

        # 对特征进行哈希并加权累加
        for token, weight in features.items():
            token_hash = self._hash(token)
            for i in range(self.hash_size):
                bitmask = 1 << i
                if token_hash & bitmask:
                    v[i] += weight
                else:
                    v[i] -= weight

        # 计算最终的哈希值
        fingerprint = 0
        for i in range(self.hash_size):
            if v[i] > 0:
                fingerprint |= 1 << i

        return fingerprint

    def _hash(self, token):
        """将单个token转换为固定长度的整数。"""
        return int.from_bytes(token.encode('utf-8'), 'little')

    def hamming_distance(self, hash1, hash2):
        """计算两个哈希值之间的汉明距离。"""
        x = hash1 ^ hash2
        return bin(x).count('1')

# 加载停用词
def load_stopwords(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        stopwords = set(line.strip() for line in file)
    return stopwords

# 读取自定义短语
def load_phrases(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        phrases = [line.strip() for line in file]
    return phrases

# 读取Word文档内容
def read_docx(file_path):
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


# 读取代码文件内容的函数
def read_code_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        code = file.read()
    return code


# 提取代码中的函数名、类名和变量名
def extract_keywords_with_ast(code):
    tree = ast.parse(code)
    keywords = set()

    class KeywordExtractor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            keywords.add(node.name)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            keywords.add(node.name)
            self.generic_visit(node)

    extractor = KeywordExtractor()
    extractor.visit(tree)

    return keywords


# 分析函数和类之间的依赖关系
def analyze_dependencies(code):
    tree = ast.parse(code)
    dependencies = {}

    class DependencyAnalyzer(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            func_name = node.name
            calls = [n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
            dependencies[func_name] = calls
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            class_name = node.name
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            dependencies[class_name] = methods
            self.generic_visit(node)

    analyzer = DependencyAnalyzer()
    analyzer.visit(tree)

    return dependencies


# 对代码文本进行预处理（移除注释和空行，并提取标识符）
def preprocess_code(code):
    lines = code.split('\n')
    processed_lines = []
    in_multiline_comment = False
    for line in lines:
        line = line.strip()
        if line.startswith('"""') or line.startswith("'''"):
            in_multiline_comment = not in_multiline_comment
            continue
        if in_multiline_comment or line.startswith('#') or not line:
            continue
        # 提取标识符（变量名、函数名等）
        identifiers = re.findall(r'\b[a-zA-Z_]\w*\b', line)
        processed_lines.extend(identifiers)
    return ' '.join(processed_lines)


# 读取Excel文件内容的函数
def read_excel(file_path):
    df = pd.read_excel(file_path)
    # 将所有单元格的内容合并成一个字符串
    full_text = ' '.join(df.astype(str).apply(' '.join, axis=1))
    return full_text


# 提取关键词的函数
def extract_keywords(text, stopwords, phrases, topK=10):
    # 替换短语
    for phrase in phrases:
        text = text.replace(phrase, '_'.join(phrase.split()))

    # 使用 jieba 的 TextRank 方法提取关键词，设置词性过滤
    keywords = jieba.analyse.textrank(text, topK=topK, withWeight=True, allowPOS=('ns', 'n', 'vn', 'v'))
    # 过滤停用词
    keywords = [(kw, weight) for kw, weight in keywords if kw not in stopwords]

    # 如果 TextRank 未能提取到关键词，尝试使用 TF-IDF 方法
    if not keywords:
        print("TextRank未能提取到关键词。尝试使用TF-IDF方法。")
        keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=True, allowPOS=('ns', 'n', 'vn', 'v'))
        keywords = [(kw, weight) for kw, weight in keywords if kw not in stopwords]

    # 恢复短语
    keywords = [(kw.replace('_', ' '), weight) for kw, weight in keywords]

    return keywords


# 关键词提取主函数，根据文件类型进行处理
# 输入文件路径，返回提取的特征字符串
def extraction(file_path):
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    if file_extension == '.docx':
        text = read_docx(file_path)
    elif file_extension == '.xlsx':
        text = read_excel(file_path)
    elif file_extension == '.py':
        code_text = read_code_file(file_path)
        keywords = extract_keywords_with_ast(code_text)
        dependencies = analyze_dependencies(code_text)

        # 输出相关信息
        output = []

        # 查找含有关键词的函数及其依赖关系
        for func, deps in dependencies.items():
            if keywords.intersection(set(func.split())):
                output.append(func)
                for dep in deps:
                    if keywords.intersection(set(dep.split())):
                        output.append(f"  {dep}")

        # 查找含有关键词的类及其方法
        for cls, methods in dependencies.items():
            if keywords.intersection(set(cls.split())):
                output.append(cls)
                for method in methods:
                    if keywords.intersection(set(method.split())):
                        output.append(f"  {method}")

        # 移除重复条目
        output = list(dict.fromkeys(output))

        # 输出最终结果
        final_output = " ".join(output)
        print("Final Output:")
        print(final_output)

        return final_output

    else:
        raise ValueError("Unsupported file type")

    # 加载停用词和自定义短语
    stopwords = load_stopwords(STOPWORDS_PATH)
    phrases = load_phrases(PHRASES_PATH)

    # 提取关键词
    keywords = extract_keywords(text, stopwords, phrases, topK=20)

    formatted_elements = [
        f"{keyword}{weight:.4f}"
        for keyword, weight in keywords
    ]
    formatted_string = ' '.join(formatted_elements)
    if len(formatted_string) > 99:
        formatted_string = formatted_string[:99]

    return formatted_string

# 输入文件路径和各种水印信息，返回生成的零水印
# file_path文件路径, time水印时间, role用户角色, userId用户id, userName用户名, userIp用户IP, channel数据渠道, hashedData零水印
def watermark(file_path, time, role, userId, userName, userIp, channel):
    # 替换为你自己的文件路径
    feature = extraction(file_path)

    perceptual_hash = PerceptualHash()
    # 感知哈希
    hashedFeature = perceptual_hash.compute(feature)
    # 拼接
    data = f"{hashedFeature}-{time}-{role}-{userId}-{userName}-{userIp}-{channel}"
    # SHA256哈希
    hash = hashlib.sha256(data.encode()).hexdigest()

    print("hash:")
    print(hash)
    return hash

