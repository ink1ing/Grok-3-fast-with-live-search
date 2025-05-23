#!/bin/bash

# Grok 3.0 Chat Application Deployment Check Script
echo "🔍 Grok 3.0 部署检查..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

echo "📋 检查系统依赖..."

# Check Python
if command_exists python; then
    PYTHON_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}✅ Python: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 未安装${NC}"
    exit 1
fi

# Check pip
if command_exists pip; then
    echo -e "${GREEN}✅ pip 已安装${NC}"
else
    echo -e "${RED}❌ pip 未安装${NC}"
    exit 1
fi

echo ""
echo "📦 检查Python依赖..."

# Check if requirements.txt exists
if [ -f requirements.txt ]; then
    echo -e "${GREEN}✅ requirements.txt 存在${NC}"
    
    # Try to install dependencies
    echo "📥 安装依赖..."
    pip install -r requirements.txt > /dev/null 2>&1
    print_status $? "依赖安装"
else
    echo -e "${RED}❌ requirements.txt 不存在${NC}"
    exit 1
fi

echo ""
echo "📁 检查项目文件..."

# Check essential files
files=("chat.py" "templates/index.html" "start.sh" "env.example")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        print_status 0 "$file 存在"
    else
        print_status 1 "$file 缺失"
    fi
done

echo ""
echo "🔧 检查配置..."

# Check environment variables
echo "环境变量检查:"
echo "  MODEL_NAME: ${MODEL_NAME:-'未设置 (将使用默认值: grok-3-fast-latest)'}"
echo "  API_URL: ${API_URL:-'未设置 (将使用默认值: https://api.x.ai/v1/chat/completions)'}"
echo "  PORT: ${PORT:-'未设置 (将使用默认值: 10000)'}"

echo ""
echo "🚀 启动应用测试..."

# Start application in background
export MODEL_NAME=${MODEL_NAME:-"grok-3-fast-latest"}
export PORT=${PORT:-"10000"}

echo "启动应用 (端口: $PORT)..."
python chat.py &
APP_PID=$!

# Wait for app to start
sleep 5

# Check if app is running
if kill -0 $APP_PID 2>/dev/null; then
    echo -e "${GREEN}✅ 应用启动成功 (PID: $APP_PID)${NC}"
    
    # Test health endpoint
    echo "测试健康检查端点..."
    HEALTH_RESPONSE=$(curl -s http://localhost:$PORT/health 2>/dev/null)
    if [ $? -eq 0 ] && echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        echo -e "${GREEN}✅ 健康检查通过${NC}"
        echo "响应: $HEALTH_RESPONSE"
    else
        echo -e "${RED}❌ 健康检查失败${NC}"
    fi
    
    # Test status endpoint
    echo "测试状态端点..."
    STATUS_RESPONSE=$(curl -s http://localhost:$PORT/api/status 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 状态端点正常${NC}"
        echo "响应: $STATUS_RESPONSE"
    else
        echo -e "${RED}❌ 状态端点失败${NC}"
    fi
    
    # Stop the application
    echo "停止测试应用..."
    kill $APP_PID
    wait $APP_PID 2>/dev/null
    echo -e "${GREEN}✅ 应用已停止${NC}"
    
else
    echo -e "${RED}❌ 应用启动失败${NC}"
    exit 1
fi

echo ""
echo "🎉 部署检查完成！"
echo ""
echo "📝 启动应用的方法:"
echo "1. 使用启动脚本: ./start.sh"
echo "2. 手动启动: MODEL_NAME=grok-3-fast-latest python chat.py"
echo "3. 使用环境文件: cp env.example .env && python chat.py"
echo ""
echo "🌐 访问地址: http://localhost:$PORT"
echo "🔍 健康检查: http://localhost:$PORT/health"
echo "📊 状态信息: http://localhost:$PORT/api/status" 