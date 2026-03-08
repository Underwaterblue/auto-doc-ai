import os
import time
import git
import shutil
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory, abort
from werkzeug.utils import secure_filename
from backend.ai_generator import generate_documentation
from backend.utils import extract_zip, analyze_code, build_prompt, read_file_with_encoding
import traceback
from github import Github, GithubException  # 用于推送

app = Flask(__name__, template_folder='../frontend/templates')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

DOCS_FOLDER = os.path.abspath('../docs')
REPO_CLONE_DIR = os.path.join(app.config['UPLOAD_FOLDER'], 'cloned_repos')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(DOCS_FOLDER, exist_ok=True)
os.makedirs(REPO_CLONE_DIR, exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/manage')
def manage_docs():
    """文档管理页面"""
    try:
        return render_template('docs.html')
    except Exception as e:
        traceback.print_exc()
        return f"模板渲染错误: {str(e)}", 500


@app.route('/generate', methods=['POST'])
def generate():
    """处理上传的文件（单文件或ZIP）"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件上传'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    doc_type = request.form.get('doc_type', 'README')
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    if filename.endswith('.zip'):
        extract_dir = os.path.join(app.config['UPLOAD_FOLDER'],
                                   'extracted_' + os.path.splitext(filename)[0])
        extract_zip(filepath, extract_dir)
        code_infos = analyze_code(extract_dir)
        prompt = build_prompt(code_infos, doc_type)
    else:
        try:
            code = read_file_with_encoding(filepath)
        except Exception as e:
            return jsonify({'error': f'读取文件失败：{str(e)}'}), 500
        prompt = f"请根据以下代码生成一份{doc_type}文档：\n\n{code}"

    documentation = generate_documentation(prompt)
    output_filename = f"{os.path.splitext(filename)[0]}_{doc_type}.md"
    output_path = os.path.join(DOCS_FOLDER, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(documentation)

    return jsonify({
        'document': documentation,
        'download': f'/docs/{output_filename}'
    })


@app.route('/clone_repo', methods=['POST'])
def clone_repo():
    """克隆远程仓库并生成文档"""
    data = request.get_json()
    repo_url = data.get('repo_url')
    token = data.get('token', None)
    doc_type = data.get('doc_type', 'README')

    if not repo_url:
        return jsonify({'error': '请提供仓库URL'}), 400

    repo_dir = os.path.join(REPO_CLONE_DIR, str(uuid.uuid4()))
    try:
        if token and '@' not in repo_url:
            if 'github.com' in repo_url:
                repo_url = repo_url.replace('https://', f'https://{token}@')
            elif 'gitlab.com' in repo_url:
                repo_url = repo_url.replace('https://', f'https://oauth2:{token}@')
        git.Repo.clone_from(repo_url, repo_dir, depth=1)
    except Exception as e:
        return jsonify({'error': f'克隆失败: {str(e)}'}), 500

    try:
        code_infos = analyze_code(repo_dir)
        prompt = build_prompt(code_infos, doc_type)
        documentation = generate_documentation(prompt)

        safe_repo_name = repo_url.split('/')[-1].replace('.git', '') or 'repo'
        output_filename = f"{safe_repo_name}_{doc_type}.md"
        output_path = os.path.join(DOCS_FOLDER, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(documentation)
        download_link = f'/docs/{output_filename}'
    except Exception as e:
        documentation = f"分析或生成失败: {str(e)}"
        download_link = None
    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)

    return jsonify({
        'document': documentation,
        'repo_url': repo_url,
        'download': download_link
    })


# ---------- 新增：推送文档到 GitHub ----------
@app.route('/push_to_github', methods=['POST'])
def push_to_github():
    data = request.get_json()
    token = data.get('token')
    repo_name = data.get('repo')          # e.g. "Underwaterblue/auto-doc-ai"
    branch = data.get('branch', 'main')
    file_path = data.get('file_path')      # e.g. "README.md"
    commit_message = data.get('commit_message', 'Update documentation via AI')
    content = data.get('content')

    if not all([token, repo_name, file_path, content]):
        return jsonify({'error': '缺少必要参数'}), 400

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        try:
            # 尝试获取文件，如果存在则更新，否则创建
            contents = repo.get_contents(file_path, ref=branch)
            repo.update_file(contents.path, commit_message, content, contents.sha, branch=branch)
        except GithubException as e:
            if e.status == 404:  # 文件不存在
                repo.create_file(file_path, commit_message, content, branch=branch)
            else:
                raise
        return jsonify({'success': True, 'message': f'成功推送到 {repo_name}/{file_path}'})
    except Exception as e:
        return jsonify({'error': f'推送失败: {str(e)}'}), 500


@app.route('/docs', methods=['GET'])
def list_docs():
    """列出所有已生成的文档"""
    if not os.path.exists(DOCS_FOLDER):
        return jsonify([])
    files = []
    for fname in os.listdir(DOCS_FOLDER):
        filepath = os.path.join(DOCS_FOLDER, fname)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                'name': fname,
                'size': stat.st_size,
                'modified': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
            })
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify(files)


@app.route('/docs/<path:filename>', methods=['GET'])
def download_doc(filename):
    """下载指定文档"""
    if '..' in filename or filename.startswith('/'):
        abort(404)
    return send_from_directory(DOCS_FOLDER, filename, as_attachment=True)


@app.route('/docs/<path:filename>', methods=['DELETE'])
def delete_doc(filename):
    """删除指定文档"""
    if '..' in filename or filename.startswith('/'):
        abort(404)
    filepath = os.path.join(DOCS_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True, 'message': '删除成功'})
    else:
        abort(404)


if __name__ == '__main__':
    app.run(debug=True)