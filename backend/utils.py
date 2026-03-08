import ast
import os
import zipfile
import re

def read_file_with_encoding(filepath):
    """
    尝试多种编码读取文件，返回字符串。
    如果所有常见编码都失败，则用 latin-1 保底（不会抛出异常，但可能乱码）。
    """
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(filepath, 'rb') as f:
        return f.read().decode('latin-1')


def extract_zip(zip_path, extract_to):
    """解压ZIP文件到指定目录"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return extract_to


# ---------- 多语言解析函数 ----------
def analyze_python_file(filepath):
    """分析单个Python文件，提取函数和类定义及其文档字符串"""
    content = read_file_with_encoding(filepath)
    try:
        tree = ast.parse(content)
    except Exception:
        return []  # 解析失败则跳过
    result = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            elem_type = 'function' if isinstance(node, ast.FunctionDef) else 'class'
            doc = ast.get_docstring(node) or ''
            result.append({
                'type': elem_type,
                'name': node.name,
                'doc': doc
            })
    return result


def analyze_js_file(filepath):
    """简单解析 JavaScript 文件，提取函数名"""
    content = read_file_with_encoding(filepath)
    functions = re.findall(r'function\s+(\w+)\s*\(', content)
    # 匹配箭头函数：const func = (...) => ...
    arrow_funcs = re.findall(r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>', content)
    all_funcs = functions + arrow_funcs
    result = []
    for func in all_funcs:
        result.append({'type': 'function', 'name': func, 'doc': ''})
    return result


def analyze_java_file(filepath):
    """简单解析 Java 文件，提取类名和方法名"""
    content = read_file_with_encoding(filepath)
    classes = re.findall(r'class\s+(\w+)', content)
    # 匹配 public/private 等方法
    methods = re.findall(r'(public|private|protected)?\s+\w+\s+(\w+)\s*\(', content)
    method_names = [m[1] for m in methods]
    result = []
    for cls in classes:
        result.append({'type': 'class', 'name': cls, 'doc': ''})
    for method in method_names:
        result.append({'type': 'method', 'name': method, 'doc': ''})
    return result


def analyze_code(directory):
    """分析目录中的代码，支持多种语言"""
    infos = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            if file.endswith('.py'):
                infos += analyze_python_file(filepath)
            elif file.endswith('.js'):
                infos += analyze_js_file(filepath)
            elif file.endswith('.java'):
                infos += analyze_java_file(filepath)
            # 可以继续添加更多语言的支持
    return infos


def build_prompt(code_infos, doc_type='README'):
    """根据代码结构信息和文档类型构建prompt"""
    if doc_type == 'README':
        prompt = "请根据如下代码结构生成项目说明文档（README.md），包括简介、安装、用法、依赖分析等：\n"
    elif doc_type == 'API文档':
        prompt = "请根据代码结构生成详细API文档，包含所有接口、参数、返回值说明，示例代码：\n"
    elif doc_type == '用户手册':
        prompt = "请生成用户手册，包含操作流程、部署、常见问题：\n"
    else:
        prompt = f"请根据如下代码结构生成结构化文档：\n"

    for info in code_infos:
        prompt += f"{info['type']}: {info['name']} 描述: {info['doc']}\n"
    return prompt