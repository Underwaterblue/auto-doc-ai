# AI 结构化文档生成器

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)

一个基于 AI 大模型（DeepSeek）的技术文档自动生成工具。支持上传代码文件/ ZIP 包或输入 GitHub 仓库地址，自动分析代码结构，生成 README、API 文档、用户手册等结构化文档。

## 功能特性

- [x] 上传单个文件或 ZIP 包，自动分析 Python 代码（函数、类、文档字符串）
- [x] 输入公开 GitHub 仓库地址，自动克隆并分析
- [x] 调用 DeepSeek 模型生成多种类型文档（README/API/用户手册/依赖分析/部署指南）
- [x] 在线预览、编辑、复制生成的文档
- [x] 导出为 Markdown 或 HTML 文件
- [x] 自动保存所有生成文档，支持管理（查看/下载/删除）

## 技术栈

- **后端**：Python 3.13, Flask, OpenAI SDK, GitPython
- **前端**：HTML, JavaScript, Bootstrap 5
- **AI 模型**：DeepSeek（通过阿里云百炼平台）

## 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/你的用户名/auto-doc-ai.git
cd auto-doc-ai