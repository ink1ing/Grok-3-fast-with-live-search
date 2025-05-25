# 🚀 Grok-3-Fast with Live Search

A modern, responsive web interface for xAI's Grok-3-Fast model with integrated Live Search capabilities. Built with Flask, Socket.IO, and modern web technologies.

## ✨ Features

- **🤖 Grok-3-Fast Integration**: Direct access to xAI's latest Grok-3-Fast model
- **🔍 Live Search**: Real-time information from X, web pages, news, and RSS sources
- **📱 Responsive Design**: Perfect adaptation for mobile, tablet, and desktop
- **💬 Real-time Chat**: WebSocket-based instant messaging
- **📝 Markdown Support**: Full Markdown rendering with syntax highlighting
- **🧮 Math Formulas**: LaTeX math formula support with MathJax
- **💾 Conversation History**: Persistent chat history management
- **🎨 Modern UI**: GitHub Dark theme with smooth animations
- **⚡ Fast Deployment**: One-click deployment to Render
- **🔒 Cloud-Ready**: Enhanced DNS resolution and SSL handling for cloud platforms

## 🚀 Quick Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Click the "Deploy to Render" button above
2. Connect your GitHub account and fork this repository
3. Set your xAI API key in the Render dashboard environment variables
4. Deploy and enjoy!

## 🛠️ Local Development

### Prerequisites

- Python 3.8+
- xAI API Key (get one from [xAI Console](https://console.x.ai))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ink1ing/groklocalweb.git
   cd groklocalweb
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   cp env.example .env
   # Edit .env and add your xAI API key
   ```

4. **Run the application**
   ```bash
   ./start.sh
   # Or manually:
   MODEL_NAME=grok-3-fast-latest python chat.py
   ```

5. **Open your browser**
   ```
   http://localhost:10000
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `grok-3-fast-latest` | xAI model to use |
| `API_URL` | `https://api.x.ai/v1/chat/completions` | xAI API endpoint |
| `API_IP` | `146.75.33.95` | Backup IP address for API (for DNS issues) |
| `TEMPERATURE` | `0` | Model temperature (0-1) |
| `PORT` | `10000` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `DEBUG` | `false` | Debug mode |
| `RENDER` | `false` | Set to `true` when running on Render platform |
| `DNS_SERVERS` | `8.8.8.8,1.1.1.1` | Custom DNS servers for resolution |

### Supported Models

- `grok-3-fast-latest` (Recommended)
- `grok-3-beta`
- `grok-3-fast`

## 📱 Features Overview

### Live Search Integration
- **Real-time Information**: Get the latest data from multiple sources
- **Smart Search**: Automatic search decision based on query context
- **Multiple Sources**: X (Twitter), web pages, news, RSS feeds
- **Accurate Results**: Enhanced response accuracy with current information

### Cloud-Ready Enhancements
- **Robust DNS Resolution**: Custom DNS resolvers to avoid lookup failures
- **IP Direct Connect**: Automatically uses IP direct connection when DNS fails
- **SSL Recursion Fix**: Prevents Python SSL recursion errors in cloud environments
- **Multi-level Fallbacks**: HTTP client fallbacks ensure reliable API connection
- **Detailed Diagnostics**: Enhanced logging for troubleshooting

### Modern Interface
- **Responsive Design**: Works perfectly on all devices
- **Dark Theme**: Easy on the eyes with GitHub Dark styling
- **Smooth Animations**: Fluid transitions and interactions
- **Touch Optimized**: Mobile-friendly touch interactions

### Advanced Features
- **Markdown Rendering**: Full support for Markdown syntax
- **Code Highlighting**: Syntax highlighting for 100+ languages
- **Math Formulas**: LaTeX math rendering with MathJax
- **Conversation Management**: Save, load, and delete conversations
- **Real-time Updates**: WebSocket-based instant messaging

## 🌐 Deployment Options

### Render (Recommended)
- One-click deployment with `render.yaml`
- Automatic builds and deployments
- Free tier available
- Custom domain support
- Enhanced DNS and SSL handling for Render environment

### Heroku
```bash
# Create Heroku app
heroku create your-app-name

# Set environment variables
heroku config:set MODEL_NAME=grok-3-fast-latest

# Deploy
git push heroku main
```

### Docker
```bash
# Build image
docker build -t grok3-fast .

# Run container
docker run -p 10000:10000 -e MODEL_NAME=grok-3-fast-latest grok3-fast
```

## 🔒 Security

- **API Key Protection**: Client-side storage, never sent to server logs
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Built-in request throttling
- **SSL/TLS**: HTTPS enforcement in production
- **XSS Protection**: Content Security Policy headers

## 🛠️ Troubleshooting

### SSL Issues
If you encounter SSL recursion errors, check the `SSL_FIX.md` document for details on the implemented solution. The app includes several layers of SSL error handling to ensure reliable operation in cloud environments.

### DNS Resolution Problems
For DNS resolution issues, see `RENDER_FIXES.md` for the implemented fixes. The application can automatically switch to IP direct connection when DNS resolution fails.

### Testing Tools
- Run `python test_ssl_fix.py` to verify SSL fixes
- Visit `/socket-test` endpoint to test WebSocket connectivity
- Check `/health` endpoint for application status
- Use `/api/status` to verify API configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [xAI](https://x.ai) for the Grok API
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Socket.IO](https://socket.io/) for real-time communication
- [Marked.js](https://marked.js.org/) for Markdown rendering
- [Highlight.js](https://highlightjs.org/) for syntax highlighting
- [MathJax](https://www.mathjax.org/) for math formula rendering

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ink1ing/groklocalweb/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ink1ing/groklocalweb/discussions)
- **Documentation**: [Wiki](https://github.com/ink1ing/groklocalweb/wiki)

---

**Made with ❤️ by the Grok Community**

⭐ Star this repository if you find it helpful!