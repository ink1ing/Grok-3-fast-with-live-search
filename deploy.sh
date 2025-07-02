#!/bin/bash

# Grok 3.0 Chat Application 部署脚本
# 支持本地开发和云端部署

set -e

echo "🚀 Grok 3.0 Chat Application 部署脚本"
echo "======================================"

# 检查Python版本
echo "📋 检查环境..."
python_version=$(python --version 2>&1)
echo "Python版本: $python_version"

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "⬆️  升级pip..."
pip install --upgrade pip

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "⚙️  创建环境变量文件..."
    cp env.example .env
    echo "请编辑 .env 文件并添加您的配置"
fi

# 运行测试
echo "🧪 运行测试..."
python test_live_search.py

echo ""
echo "✅ 部署完成！"
echo ""
echo "🌐 本地开发:"
echo "   python chat.py"
echo "   然后访问 http://localhost:10000"
echo ""
echo "☁️  云端部署:"
echo "   - Render: 推送到GitHub并连接到Render"
echo "   - Heroku: heroku create && git push heroku main"
echo ""
echo "�� 更多信息请查看 README.md" 