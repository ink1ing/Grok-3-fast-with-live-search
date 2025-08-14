# 🚀 Grok 3.0 Chat Application

一个基于 Flask 和 Socket.IO 的现代化实时聊天应用，集成了 xAI 的 Grok 3.0 API 和 Live Search 功能。

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## ✨ 功能特点

- 🤖 **Grok 3.0 AI 对话** - 集成最新的 xAI Grok 3.0 API
- 🔍 **Live Search 实时搜索** - 获取来自 X、网页、新闻和 RSS 源的最新信息
- 💬 **实时聊天界面** - 基于 WebSocket 的流畅对话体验
- 📱 **响应式设计** - 完美支持桌面端和移动端
- 🗂️ **会话历史管理** - 自动保存和管理对话历史
- 🔄 **自动重连机制** - 网络断开时自动重新连接
- 🎨 **现代化 UI** - 深色主题，优雅的用户界面
- ☁️ **云端部署优化** - 针对 Render、Heroku 等云平台优化

## 🔍 xAI Live Search 功能

本应用集成了 xAI 的 Live Search API，提供以下特性：

- **🧠 自动搜索决策** - Grok 根据对话上下文自动判断是否需要进行实时搜索
- **🌐 多样化数据源** - 支持从 X 平台、网页、新闻和 RSS 源获取信息
- **⚡ 实时信息** - 获取最新的24小时内的信息
- **🔗 智能集成** - 搜索结果自动整合到对话回复中

> **注意**: Live Search 功能目前处于免费公开测试阶段（截止到2025年6月5日）

## 🚀 快速开始

### 本地开发

1. **克隆仓库**
```bash
git clone https://github.com/your-username/grok3.0-api.git
cd grok3.0-api
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp env.example .env
# 编辑 .env 文件，添加您的配置
```

4. **启动应用**
```bash
python chat.py
```

5. **访问应用**
打开浏览器访问 `http://localhost:10000`

### 🌐 云端部署

#### Render 部署

1. Fork 这个仓库到您的 GitHub 账户
2. 在 [Render](https://render.com) 创建新的 Web Service
3. 连接您的 GitHub 仓库
4. 配置环境变量（见下方配置说明）
5. 点击部署

#### Heroku 部署

```bash
# 安装 Heroku CLI 后执行
heroku create your-app-name
heroku config:set API_URL=https://api.x.ai/v1/chat/completions
heroku config:set MODEL_NAME=grok-4-latest
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

## ⚙️ 环境变量配置

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `API_URL` | xAI API 端点 | `https://api.x.ai/v1/chat/completions` | ✅ |
| `MODEL_NAME` | 使用的模型名称 | `grok-4-latest` | ✅ |
| `TEMPERATURE` | 模型温度参数 | `0` | ❌ |
| `SECRET_KEY` | Flask 密钥 | 随机生成 | ✅ |
| `DEBUG` | 调试模式 | `False` | ❌ |
| `PORT` | 服务器端口 | `10000` | ❌ |
| `HOST` | 服务器主机 | `0.0.0.0` | ❌ |

## 🔑 获取 xAI API 密钥

1. 访问 [xAI 控制台](https://console.x.ai)
2. 创建新的 API 密钥
3. 在应用设置中输入您的 API 密钥
4. 开启 Live Search 功能（可选）

## 📱 使用说明

1. **设置 API 密钥** - 点击设置按钮，输入您的 xAI API 密钥
2. **开启 Live Search** - 在设置中启用实时搜索功能
3. **开始对话** - 在输入框中输入消息，按回车发送
4. **管理会话** - 在左侧边栏查看和管理对话历史
5. **新建对话** - 点击"Start a New Talk"开始新的对话

## 🛠️ 技术栈

- **后端**: Flask, Socket.IO, Python
- **前端**: HTML5, CSS3, JavaScript (ES6+)
- **API**: xAI Grok 3.0 API with Live Search
- **部署**: Gunicorn, Eventlet
- **云平台**: Render, Heroku, Railway 等

## 📊 API 端点

- `GET /` - 主页面
- `GET /health` - 健康检查端点
- `GET /api/status` - 应用状态信息
- `WebSocket /socket.io` - 实时通信

## 🔧 开发

### 项目结构

```
grok3.0-api/
├── chat.py              # 主应用文件
├── templates/
│   └── index.html       # 前端模板
├── requirements.txt     # Python 依赖
├── Procfile            # 部署配置
├── env.example         # 环境变量示例
├── test_live_search.py # 测试脚本
└── README.md           # 项目文档
```

### 运行测试

```bash
python test_live_search.py
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [xAI](https://x.ai) - 提供强大的 Grok 3.0 API 和 Live Search 功能
- [Flask](https://flask.palletsprojects.com/) - 优秀的 Python Web 框架
- [Socket.IO](https://socket.io/) - 实时通信解决方案

## 📞 支持

如果您遇到问题或有任何建议，请：

1. 查看 [Issues](https://github.com/your-username/grok3.0-api/issues)
2. 创建新的 Issue
3. 联系开发者

---

**Built with ❤️ by Ink 🧑🏻‍💻**
