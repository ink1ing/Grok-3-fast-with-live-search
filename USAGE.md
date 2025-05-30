# 🚀 Grok 3.0 Chat 使用说明

## 📱 快速开始

### 1. 启动应用
```bash
python chat.py
```
应用将在 `http://localhost:10000` 启动

### 2. 设置API密钥
1. 打开浏览器访问 `http://localhost:10000`
2. 点击左下角的设置按钮（⚙️齿轮图标）
3. 输入您的xAI API密钥：
   ```
   xai-VT2kiahrHp06P6HXSECndDVKZIeIQmkmi44LONOsZuun7ENEeqnSSB9G3fJnGoweJ2izUSONx7t8sXCE
   ```
4. 启用Live Search功能（可选）
5. 点击"Save"保存

### 3. 开始聊天
- 在输入框中输入您的问题
- 按Enter键或点击"Send"按钮发送
- Grok 3.0将为您提供智能回复

## ✨ 功能特性

### 🤖 Grok 3.0 Fast 模型
- 使用最新的 `grok-3-fast-latest` 模型
- 快速响应，高质量对话
- 支持多轮对话上下文

### 🔍 Live Search 实时搜索
- 自动判断是否需要搜索最新信息
- 支持X平台、网页、新闻、RSS源
- 获取24小时内的最新数据
- 智能整合搜索结果到回复中

### 💬 对话管理
- 自动保存对话历史
- 支持多个对话会话
- 可以删除不需要的对话
- 点击"Start a New Talk"开始新对话

### 📱 响应式设计
- 支持桌面和移动设备
- 深色主题，护眼舒适
- 流畅的动画效果

## 🔧 故障排除

### API密钥问题
- 确保API密钥格式正确（以`xai-`开头）
- 检查API密钥是否有效且未过期
- 确保网络连接正常

### 连接问题
- 检查应用是否正常启动
- 访问 `http://localhost:10000/health` 检查健康状态
- 确保端口10000未被其他程序占用

### 消息发送失败
- 检查API密钥设置
- 确认网络连接稳定
- 查看浏览器控制台错误信息

## 📊 监控端点

- **健康检查**: `http://localhost:10000/health`
- **API状态**: `http://localhost:10000/api/status`
- **测试页面**: `http://localhost:10000/test`

## 🎯 使用技巧

1. **启用Live Search**: 对于需要最新信息的问题，建议启用Live Search功能
2. **多轮对话**: 系统会记住对话上下文，可以进行连续对话
3. **新对话**: 讨论新话题时，点击"Start a New Talk"获得更好的体验
4. **移动端**: 在手机上使用时，点击左上角的☰按钮打开侧边栏

## 💡 示例对话

```
用户: 今天有什么重要的科技新闻？
Grok: [启用Live Search后会搜索最新科技新闻并回复]

用户: 解释一下量子计算的基本原理
Grok: [提供详细的量子计算解释]

用户: 帮我写一个Python函数来计算斐波那契数列
Grok: [提供完整的Python代码示例]
```

## 🔒 隐私说明

- API密钥存储在浏览器本地存储中
- 对话历史保存在应用内存中
- 应用重启后历史记录会清空
- 不会向第三方发送您的数据 