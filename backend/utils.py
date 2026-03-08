import ast
import os
import zipfile

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
    # 最后尝试以二进制读取并用 latin-1 解码（永远不会失败）
    with open(filepath, 'rb') as f:
        return f.read().decode('latin-1')


def extract_zip(zip_path, extract_to):
    """解压ZIP文件到指定目录"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return extract_to


def analyze_code(directory):
    """分析目录中的Python代码，返回函数/类信息列表"""
    return analyze_python(directory)


def analyze_python(root_dir):
    """遍历目录，收集所有Python文件的结构信息"""
    infos = []
    for dirpath, _, files in os.walk(root_dir):
        for fname in files:
            if fname.endswith('.py'):
                infos += analyze_python_file(os.path.join(dirpath, fname))
    return infos


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