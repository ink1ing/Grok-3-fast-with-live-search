#!/usr/bin/env python3
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO
import requests
import json
import os
import logging
import sys
import time
import ssl
from datetime import datetime
from dotenv import load_dotenv
import urllib.request
import urllib.error
import http.client
import socket

# Load environment variables from .env file
load_dotenv()

# Configure detailed logging system first
logging.basicConfig(
    level=logging.DEBUG,  # Set DEBUG level to get more detailed information
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===== Fix SSL Recursion Error =====
logger.info("Applying SSL fix to avoid recursion errors...")

try:
    # 递归错误检测函数
    def debug_recursion():
        import sys
        import traceback
        
        frame = sys._getframe()
        frames = []
        visited = set()
        
        # 收集调用栈信息
        while frame:
            frame_id = id(frame)
            if frame_id in visited:
                logger.critical("RECURSION DETECTED IN CALL STACK!")
                for i, f in enumerate(frames):
                    logger.critical(f"Frame {i}: {f.f_code.co_filename}:{f.f_lineno} in {f.f_code.co_name}")
                return True
            visited.add(frame_id)
            frames.append(frame)
            frame = frame.f_back
        
        return False
    
    # 使用更安全的方式避免SSL递归错误
    import urllib3
    
    # 禁用urllib3警告
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.debug("urllib3 warnings disabled")
    
    # 创建一个全局的SSL上下文，不进行证书验证
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')  # 允许更宽松的密码套件
    logger.debug("Created custom SSL context with verification disabled")
    
    # 保存原始的SSL方法
    original_default_https_context = getattr(ssl, '_create_default_https_context', None)
    
    # 定义一个安全的创建SSL上下文的函数
    def safe_create_context(*args, **kwargs):
        logger.debug("Using safe SSL context creation method")
        return ssl_context
    
    # 替换SSL方法
    if hasattr(ssl, '_create_default_https_context'):
        ssl._create_default_https_context = safe_create_context
    
    # 修改requests库的会话设置，避免递归
    old_merge_environment_settings = requests.Session.merge_environment_settings
    
    def patched_merge_environment_settings(self, url, proxies, stream, verify, cert):
        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False
        return settings
    
    requests.Session.merge_environment_settings = patched_merge_environment_settings
    logger.debug("Patched requests session settings")
    
    # 修改urllib3的SSL验证方式
    urllib3.util.ssl_.create_default_context = safe_create_context
    logger.debug("Modified urllib3 SSL context creation")
    
    # 禁用requests的SSL警告
    requests.packages.urllib3.disable_warnings()
    
    logger.info("SSL fix successfully applied")
except Exception as e:
    logger.error(f"Error applying SSL fix: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# Function to log detailed exception information
def log_exception(e, prefix="Error"):
    """Log detailed exception information, including stack trace"""
    import traceback
    error_trace = traceback.format_exc()
    logger.error(f"{prefix}: {str(e)}")
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Stack trace:\n{error_trace}")
    return error_trace

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')

# Configure SocketIO with cloud-friendly options
socketio = SocketIO(
    app,
    cors_allowed_origins="*",     # Allow cross-origin requests
    ping_timeout=90,              # 增加ping超时时间
    ping_interval=25,             # 保持良好的ping间隔
    async_mode='eventlet',        # 在Render上使用eventlet，与gunicorn配置一致
    manage_session=True,          # 自动管理session
    logger=True,                  # 在调试阶段开启日志
    engineio_logger=True,         # 在调试阶段开启Engine.IO日志
    cookie=False                  # 避免cookie问题
)

# API endpoint for Grok API
API_URL = os.getenv('API_URL', 'https://api.x.ai/v1/chat/completions')
# 备用API IP地址（用于DNS解析失败时）
API_IP = os.getenv('API_IP', '146.75.33.95')  # api.x.ai的IP地址

# 配置DNS解析器
def configure_dns():
    """配置可靠的DNS解析器"""
    try:
        import dns.resolver
        # 使用Google的DNS服务器
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
        return resolver
    except ImportError:
        logger.warning("dnspython未安装，无法使用自定义DNS解析器")
        return None
    except Exception as e:
        logger.error(f"配置DNS解析器失败: {str(e)}")
        return None

# 尝试配置DNS解析器
dns_resolver = configure_dns()

# 解析域名为IP地址
def resolve_hostname(hostname):
    """解析主机名为IP地址"""
    try:
        if dns_resolver:
            # 使用自定义DNS解析器
            answers = dns_resolver.resolve(hostname, 'A')
            for rdata in answers:
                return str(rdata)
        
        # 备用方法：使用socket
        import socket
        return socket.gethostbyname(hostname)
    except Exception as e:
        logger.error(f"无法解析主机名 {hostname}: {str(e)}")
        return None

# Session management for chats, API keys and settings
# Efficient memory management using class-based approach
class SessionManager:
    def __init__(self, max_conversations=50, max_messages_per_conversation=30):
        """Initialize the session manager with memory limits
        
        Args:
            max_conversations: Maximum number of conversations to keep in memory
            max_messages_per_conversation: Maximum messages per conversation
        """
        self.conversation_history = {}  # Stores all conversation data
        self.user_api_keys = {}         # Maps session IDs to API keys
        self.user_live_search_settings = {}  # Maps session IDs to Live Search settings
        self.max_conversations = max_conversations
        self.max_messages_per_conversation = max_messages_per_conversation
    
    def sanitize_message(self, message):
        """Clean and validate message data to ensure proper format and remove invalid data
        
        Args:
            message: The message object to sanitize
            
        Returns:
            A cleaned message object or None if invalid
        """
        try:
            if not isinstance(message, dict):
                logger.warning(f"Invalid message format: {type(message)}")
                return None
            
            # Ensure required fields exist
            if 'role' not in message or 'content' not in message:
                logger.warning("Message missing required fields")
                return None
            
            # Clean and validate role field
            role = str(message.get('role', '')).strip().lower()
            if role not in ['system', 'user', 'assistant']:
                logger.warning(f"Invalid message role: {role}")
                role = 'user'  # Default to user message
            
            # Clean content field
            content = str(message.get('content', '')).strip()
            if not content:
                logger.warning("Empty message content")
                return None
            
            # Limit content length
            if len(content) > 10000:
                logger.warning(f"Message content too long ({len(content)} chars), truncating")
                content = content[:10000] + "..."
            
            # Create clean message object
            clean_message = {
                'role': role,
                'content': content,
                'timestamp': message.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            }
            
            return clean_message
        except Exception as e:
            logger.error(f"Error cleaning message: {str(e)}")
            return None
    
    def cleanup_old_conversations(self):
        """Remove oldest conversations when limit is reached to save memory"""
        try:
            if len(self.conversation_history) > self.max_conversations:
                # Sort by timestamp and keep only the newest conversations
                sorted_convs = sorted(
                    self.conversation_history.items(),
                    key=lambda x: x[1].get('timestamp', ''),
                    reverse=True
                )[:self.max_conversations]
                # Create new dictionary directly instead of modifying existing one
                self.conversation_history = {cid: conv for cid, conv in sorted_convs}
                logger.info(f"Cleaned up old conversations, current count: {len(self.conversation_history)}")
        except Exception as e:
            logger.error(f"Error cleaning up old conversations: {str(e)}")
    
    def add_message_to_conversation(self, conversation_id, message):
        """Add a message to conversation, cleaning up old messages if needed
        
        Args:
            conversation_id: ID of the conversation
            message: Message object to add
            
        Raises:
            RuntimeError: If message can't be added
        """
        try:
            # Clean the message data
            clean_message = self.sanitize_message(message)
            if not clean_message:
                logger.warning(f"Skipping invalid message for conversation: {conversation_id}")
                return
            
            # Create new conversation if it doesn't exist
            if conversation_id not in self.conversation_history:
                self.conversation_history[conversation_id] = {
                    'messages': [],
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'title': clean_message.get('content', '')[:30] + '...' if len(clean_message.get('content', '')) > 30 else clean_message.get('content', '')
                }
            
            conv = self.conversation_history[conversation_id]
            messages = conv['messages']
            
            # If message count exceeds limit, remove older messages
            if len(messages) >= self.max_messages_per_conversation:
                # Keep system messages and most recent user/assistant messages
                system_messages = [msg for msg in messages if msg.get('role') == 'system']
                other_messages = [msg for msg in messages if msg.get('role') != 'system']
                
                # Calculate how many non-system messages to keep
                keep_count = max(1, self.max_messages_per_conversation - len(system_messages))
                # Keep only the newest messages
                kept_messages = system_messages + other_messages[-keep_count:]
                
                # Replace message list
                conv['messages'] = kept_messages
                logger.debug(f"Conversation {conversation_id} messages after cleanup: {len(kept_messages)}")
            
            # Add new message
            conv['messages'].append(clean_message)
            # Update timestamp
            conv['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.debug(f"Message added to conversation {conversation_id}, current count: {len(conv['messages'])}")
            
            # Periodically clean up old conversations
            if len(self.conversation_history) > self.max_conversations:
                self.cleanup_old_conversations()
                
        except Exception as e:
            error_trace = log_exception(e, f"Error adding message to conversation {conversation_id}")
            raise RuntimeError(f"Failed to add message to conversation: {str(e)}")
    
    def get_conversation_messages(self, conversation_id):
        """Get messages for a specific conversation
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List of messages or empty list if conversation doesn't exist
        """
        try:
            messages = self.conversation_history.get(conversation_id, {}).get('messages', [])
            # Return a copy of messages list to avoid reference issues
            return list(messages)
        except Exception as e:
            logger.error(f"Error getting conversation messages: {str(e)}")
            return []
            
    def get_conversation_count(self):
        """Get the current number of conversations"""
        return len(self.conversation_history)
        
    def clear_old_data(self):
        """Periodically clean up expired data (conversations older than 24 hours)"""
        try:
            # Clean up conversations older than 24 hours
            current_time = datetime.now()
            old_conversations = []
            
            for cid, conv in self.conversation_history.items():
                try:
                    conv_time = datetime.strptime(conv['timestamp'], '%Y-%m-%d %H:%M:%S')
                    if (current_time - conv_time).days >= 1:
                        old_conversations.append(cid)
                except (ValueError, KeyError):
                    continue
            
            for cid in old_conversations:
                del self.conversation_history[cid]
                
            if old_conversations:
                logger.info(f"Cleared {len(old_conversations)} expired conversations")
        except Exception as e:
            logger.error(f"Error clearing expired data: {str(e)}")

# Initialize session manager with smaller defaults for cloud environment
session_manager = SessionManager(max_conversations=50, max_messages_per_conversation=30)
conversation_history = session_manager.conversation_history
user_api_keys = session_manager.user_api_keys
user_live_search_settings = session_manager.user_live_search_settings

# Background task to clean up old data
def cleanup_task():
    """Background task to clean up old data"""
    while True:
        try:
            session_manager.clear_old_data()
            time.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            time.sleep(60)  # Wait 1 minute before retrying if error occurs

def get_conversation_id():
    """Get current conversation ID from session or create a new one"""
    if 'conversation_id' not in session:
        session['conversation_id'] = datetime.now().strftime('%Y%m%d%H%M%S')
    return session['conversation_id']

def calculate_tokens(messages):
    """Simple token calculation method, each character counts as 1 token"""
    total_tokens = sum(len(msg['content']) for msg in messages)
    return total_tokens

def send_message(messages, api_key=None, enable_live_search=False):
    """Send messages to the API and get response, using requests library
    
    Args:
        messages: List of message objects to send
        api_key: API key for authentication
        enable_live_search: Whether to enable Live Search functionality
        
    Returns:
        Dictionary containing response or error information
    """
    if not api_key:
        logger.error("API key not set")
        return {'error': 'Please configure a valid API key in settings'}
    
    try:
        # 先检查是否已经处于递归状态
        if debug_recursion():
            logger.critical("Recursion detected before API request - using fallback method")
            return {'error': 'SSL recursion error detected, using fallback method'}
            
        # Validate message format
        if not isinstance(messages, list):
            logger.error("Invalid message format: not a list")
            return {'error': 'Invalid message format'}
        
        for msg in messages:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                logger.error("Invalid message format: missing required fields")
                return {'error': 'Invalid message format'}
        
        # Log request details
        request_id = datetime.now().strftime('%Y%m%d%H%M%S')
        logger.debug(f"API request[{request_id}] initializing: message count={len(messages)}")
        logger.debug(f"API request[{request_id}] URL: {API_URL}")
        
        # Get model info from environment variables
        model = os.getenv('MODEL_NAME', 'grok-3-fast-latest')
        temperature = float(os.getenv('TEMPERATURE', '0'))
        logger.debug(f"API request[{request_id}] model: {model}, temperature: {temperature}")
        
        # Build request data
        data = {
            'messages': messages,
            'model': model,
            'stream': False,
            'temperature': temperature
        }
        
        # Add Live Search parameters if enabled
        if enable_live_search:
            data['search_parameters'] = {
                'mode': 'auto',
                'max_search_results': 5,
                'time_range': '24h'
            }
            logger.debug(f"API request[{request_id}] Live Search enabled")
        
        # Build request headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'Grok-API-Client/1.0',
            'Host': 'api.x.ai'  # 确保请求发送到正确的主机名
        }
        
        start_time = datetime.now()
        
        # 记录内存使用情况，帮助诊断
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            logger.debug(f"API request[{request_id}] Memory usage before request: {mem_info.rss / 1024 / 1024:.2f} MB")
        except ImportError:
            logger.debug(f"API request[{request_id}] psutil not installed, skipping memory diagnostics")
        except Exception as e:
            logger.debug(f"API request[{request_id}] Error getting memory info: {str(e)}")
        
        # Use requests library with proper error handling
        import requests
        from urllib.parse import urlparse
        
        # 提取API URL的主机名
        parsed_url = urlparse(API_URL)
        hostname = parsed_url.netloc
        
        # 检查是否在Render环境中
        is_render = os.environ.get('RENDER', '').lower() == 'true'
        
        api_request_url = API_URL
        use_ip_direct = False
        retry_count = 0
        max_retries = 3
        
        # 在Render环境中尝试IP直连
        if is_render:
            logger.info(f"API request[{request_id}] 在Render环境中，尝试IP直连")
            
            # 如果提供了备用IP地址，使用IP直连
            if API_IP:
                # 构建IP直连URL
                scheme = parsed_url.scheme
                path = parsed_url.path
                ip_url = f"{scheme}://{API_IP}{path}"
                logger.info(f"API request[{request_id}] 使用IP直连: {ip_url}")
                api_request_url = ip_url
                use_ip_direct = True
            else:
                # 尝试手动解析域名
                resolved_ip = resolve_hostname(hostname)
                if resolved_ip:
                    logger.info(f"API request[{request_id}] 成功解析域名 {hostname} 为 {resolved_ip}")
                    scheme = parsed_url.scheme
                    path = parsed_url.path
                    ip_url = f"{scheme}://{resolved_ip}{path}"
                    logger.info(f"API request[{request_id}] 使用解析的IP: {ip_url}")
                    api_request_url = ip_url
        
        # 尝试使用http.client直接发送请求 - 完全绕过requests库
        try_low_level_client_first = os.environ.get('USE_LOW_LEVEL_HTTP', '').lower() == 'true'
        
        if try_low_level_client_first:
            logger.info(f"API request[{request_id}] 优先使用低级HTTP客户端")
            try:
                # 获取主机和路径
                parsed_url = urlparse(api_request_url)
                host = parsed_url.netloc
                path = parsed_url.path or '/'
                
                # 准备JSON数据
                import json
                json_data = json.dumps(data).encode('utf-8')
                
                logger.debug(f"API request[{request_id}] 尝试使用http.client连接到 {host}")
                
                # 建立连接
                conn = None
                try:
                    # 检查URL是否为HTTPS
                    is_https = parsed_url.scheme.lower() == 'https'
                    port = 443 if is_https else 80
                    
                    # 使用基本HTTP连接，但设置正确的端口
                    logger.debug(f"API request[{request_id}] 使用HTTP连接到 {host}:{port}")
                    conn = http.client.HTTPConnection(host, port, timeout=30)
                    
                    # 添加额外的请求头，以处理HTTPS请求
                    if is_https:
                        headers = dict(headers)  # 创建副本以避免修改原始字典
                        headers['X-Forwarded-Proto'] = 'https'
                    
                    # 发送请求
                    logger.debug(f"API request[{request_id}] 使用http.client发送请求")
                    conn.request(
                        "POST", 
                        path, 
                        body=json_data, 
                        headers=headers
                    )
                    
                    # 获取响应
                    http_response = conn.getresponse()
                    response_data = http_response.read().decode('utf-8')
                    
                    # 处理响应
                    if http_response.status == 200:
                        response_json = json.loads(response_data)
                        token_count = calculate_tokens(messages)
                        response_time = (datetime.now() - start_time).total_seconds()
                        
                        logger.info(f"API request[{request_id}] 低级HTTP客户端成功，总时间: {response_time}s")
                        
                        return {
                            'response': response_json,
                            'response_time': response_time,
                            'token_count': token_count
                        }
                    else:
                        logger.warning(f"API request[{request_id}] 低级HTTP客户端返回非200状态码: {http_response.status}")
                        # 继续尝试使用requests库
                except Exception as e:
                    logger.error(f"API request[{request_id}] 连接错误: {str(e)}")
                    # 继续尝试使用requests库
            except Exception as e:
                logger.error(f"API request[{request_id}] 连接错误: {str(e)}")
                # 继续尝试使用requests库
        
        # 创建带自定义SSL上下文的会话
        try:
            logger.debug(f"API request[{request_id}] 创建自定义SSL会话")
            session = requests.Session()
            
            # 直接创建适配器并设置SSL上下文
            from requests.adapters import HTTPAdapter
            from urllib3.poolmanager import PoolManager
            
            class CustomSSLAdapter(HTTPAdapter):
                def init_poolmanager(self, connections, maxsize, block=False):
                    logger.debug(f"API request[{request_id}] 初始化连接池管理器")
                    self.poolmanager = PoolManager(
                        num_pools=connections,
                        maxsize=maxsize,
                        block=block,
                        ssl_version=ssl.PROTOCOL_TLS_CLIENT,
                        ssl_context=ssl_context
                    )
            
            # 为http和https设置适配器
            adapter = CustomSSLAdapter()
            session.mount('https://', adapter)
            session.mount('http://', adapter)
            
            logger.debug(f"API request[{request_id}] 创建了自定义SSL会话")
            
        except Exception as e:
            logger.warning(f"API request[{request_id}] 无法创建自定义SSL会话: {str(e)}, 使用标准会话")
            session = requests.Session()
        
        # 设置会话不验证SSL
        session.verify = False
        
        while retry_count <= max_retries:
            try:
                # 再次检查是否已经处于递归状态
                if debug_recursion():
                    logger.critical(f"API request[{request_id}] 递归检测在请求前触发 - 使用备用方法")
                    return use_http_client_fallback(request_id, api_request_url, headers, data, messages, start_time)
                
                logger.debug(f"API request[{request_id}] 尝试 #{retry_count+1} 发送请求到 {api_request_url}")
                
                # 使用会话发送请求
                response = session.post(
                    api_request_url, 
                    json=data, 
                    headers=headers, 
                    timeout=30
                )
                
                response_time = (datetime.now() - start_time).total_seconds()
                logger.debug(f"API request[{request_id}] 响应状态码: {response.status_code}, 时间: {response_time}s")
                
                # 处理成功响应
                if response.status_code == 200:
                    response_json = response.json()
                    token_count = calculate_tokens(messages)
                    logger.info(f"API request[{request_id}] 成功，总时间: {response_time}s")
                    
                    return {
                        'response': response_json,
                        'response_time': response_time,
                        'token_count': token_count
                    }
                # 处理不同的状态码
                elif response.status_code == 401:
                    return {'error': 'Invalid or expired API key, please update your API key'}
                elif response.status_code == 403:
                    # 403错误通常是权限问题或API密钥无效
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', 'API access denied - please check your API key and permissions')
                    except:
                        error_msg = 'API access denied - please check your API key and permissions'
                    logger.error(f"API request[{request_id}] 403 错误: {error_msg}")
                    return {'error': error_msg}
                elif response.status_code == 429:
                    return {'error': 'API request rate limit exceeded, please try again later'}
                elif response.status_code == 500:
                    return {'error': 'API server error, please try again later'}
                elif response.status_code == 503:
                    return {'error': 'API service temporarily unavailable, please try again later'}
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', f'API error: {response.status_code}')
                    except:
                        error_msg = f'API error: {response.status_code}'
                    logger.error(f"API request[{request_id}] 错误 {response.status_code}: {error_msg}")
                    return {'error': error_msg}
                    
            except requests.exceptions.Timeout:
                retry_count += 1
                logger.warning(f"API request[{request_id}] 超时，重试 {retry_count}/{max_retries}")
                if retry_count > max_retries:
                    logger.error(f"API request[{request_id}] 超时，达到最大重试次数")
                return {'error': 'API request timeout, please check your network connection'}
                time.sleep(1)  # 短暂延迟后重试
                
            except requests.exceptions.ConnectionError as e:
                retry_count += 1
                logger.warning(f"API request[{request_id}] 连接错误: {str(e)}，重试 {retry_count}/{max_retries}")
                
                # 如果使用域名失败，尝试IP直连
                if not use_ip_direct and is_render:
                    logger.info(f"API request[{request_id}] 尝试切换到IP直连")
                    # 尝试手动解析域名
                    resolved_ip = resolve_hostname(hostname)
                    if resolved_ip:
                        logger.info(f"API request[{request_id}] 成功解析域名 {hostname} 为 {resolved_ip}")
                        scheme = parsed_url.scheme
                        path = parsed_url.path
                        api_request_url = f"{scheme}://{resolved_ip}{path}"
                        use_ip_direct = True
                    elif API_IP:
                        # 使用备用IP
                        scheme = parsed_url.scheme
                        path = parsed_url.path
                        api_request_url = f"{scheme}://{API_IP}{path}"
                        use_ip_direct = True
                        
                if retry_count > max_retries:
                    logger.error(f"API request[{request_id}] 连接错误，达到最大重试次数: {str(e)}")
                    return {'error': 'Network connection failed, please check your internet connection or try again later'}
                
                time.sleep(1)  # 短暂延迟后重试
                
            except RecursionError as e:
                logger.error(f"API request[{request_id}] 递归错误: {str(e)}")
                # 添加递归调用栈详情
                debug_recursion()
                
                return use_http_client_fallback(request_id, api_request_url, headers, data, messages, start_time)
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"API request[{request_id}] 请求错误: {str(e)}，重试 {retry_count}/{max_retries}")
                if retry_count > max_retries:
                    logger.error(f"API request[{request_id}] 请求错误，达到最大重试次数: {str(e)}")
                return {'error': f'API request error: {str(e)}'}
                time.sleep(1)  # 短暂延迟后重试
                    
    except RecursionError as e:
        error_trace = log_exception(e, "SSL recursion error in API request")
        # 添加递归调用栈详情
        debug_recursion()
        return {'error': 'SSL recursion error occurred. Please try again later.'}
    except Exception as e:
        error_trace = log_exception(e, "Unknown error during message send")
        return {'error': 'Unknown error occurred, please try again later'}

# 提取HTTP客户端作为独立函数，用作备用方案
def use_http_client_fallback(request_id, api_request_url, headers, data, messages, start_time):
    """使用http.client作为备用HTTP客户端
    
    当requests库发生递归错误时使用此函数作为备用方案
    """
    logger.info(f"API request[{request_id}] 尝试使用http.client作为后备方案")
    
    try:
        # 获取主机和路径
        from urllib.parse import urlparse
        parsed_url = urlparse(api_request_url)
        host = parsed_url.netloc
        path = parsed_url.path or '/'
        
        # 准备JSON数据
        import json
        json_data = json.dumps(data).encode('utf-8')
        
        logger.debug(f"API request[{request_id}] 创建http.client连接到 {host}")
        
        # 建立连接
        conn = None
        try:
            # 检查URL是否为HTTPS
            is_https = parsed_url.scheme.lower() == 'https'
            port = 443 if is_https else 80
            
            # 使用基本HTTP连接，但设置正确的端口
            logger.debug(f"API request[{request_id}] 使用HTTP连接到 {host}:{port}")
            conn = http.client.HTTPConnection(host, port, timeout=30)
            
            # 添加额外的请求头，以处理HTTPS请求
            if is_https:
                headers = dict(headers)  # 创建副本以避免修改原始字典
                headers['X-Forwarded-Proto'] = 'https'
            
            # 发送请求
            logger.debug(f"API request[{request_id}] 使用http.client发送请求")
            conn.request(
                "POST", 
                path, 
                body=json_data, 
                headers=headers
            )
            
            # 获取响应
            http_response = conn.getresponse()
            response_data = http_response.read().decode('utf-8')
            
            # 处理响应
            if http_response.status == 200:
                try:
                    response_json = json.loads(response_data)
                    token_count = calculate_tokens(messages)
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    logger.info(f"API request[{request_id}] 后备方案成功，总时间: {response_time}s")
                    
                    return {
                        'response': response_json,
                        'response_time': response_time,
                        'token_count': token_count
                    }
                except json.JSONDecodeError as je:
                    logger.error(f"API request[{request_id}] 无法解析JSON响应: {str(je)}")
                    return {'error': 'Invalid JSON response from API server'}
            elif http_response.status == 401:
                return {'error': 'Invalid or expired API key, please update your API key'}
            elif http_response.status == 403:
                return {'error': 'API access denied - please check your API key and permissions'}
            elif http_response.status == 429:
                return {'error': 'API request rate limit exceeded, please try again later'}
            else:
                logger.error(f"API request[{request_id}] 后备方案返回错误: {http_response.status}")
                return {'error': f'API error: {http_response.status}'}
                
        except http.client.HTTPException as he:
            logger.error(f"API request[{request_id}] HTTP客户端异常: {str(he)}")
            return {'error': f'HTTP connection error: {str(he)}'}
        except socket.error as se:
            logger.error(f"API request[{request_id}] 套接字错误: {str(se)}")
            return {'error': f'Network connection error: {str(se)}'}
        except Exception as conn_error:
            logger.error(f"API request[{request_id}] 连接错误: {str(conn_error)}")
            return {'error': f'Connection error: {str(conn_error)}'}
        finally:
            # 确保连接被关闭
            if conn:
                try:
                    conn.close()
                except:
                    pass
            
    except Exception as backup_error:
        logger.error(f"API request[{request_id}] 后备方案失败: {str(backup_error)}")
        import traceback
        logger.error(f"API request[{request_id}] 错误详情: {traceback.format_exc()}")
        return {'error': 'SSL recursion error occurred. Fallback method also failed. Please try again later.'}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test_page():
    """API密钥测试页面"""
    with open('test_frontend.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/health')
def health_check():
    """健康检查端点，用于云平台监控"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'features': {
            'live_search': True,
            'conversation_history': True,
            'real_time_chat': True
        }
    }

@app.route('/api/status')
def api_status():
    """API状态信息端点"""
    return {
        'api_url': API_URL,
        'model': os.getenv('MODEL_NAME', 'grok-3-fast-latest'),
        'max_conversations': session_manager.max_conversations,
        'max_messages_per_conversation': session_manager.max_messages_per_conversation,
        'current_conversations': session_manager.get_conversation_count(),
        'live_search_enabled': True
    }

@app.route('/api/validate-key', methods=['POST'])
def validate_api_key():
    """验证API密钥的有效性"""
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        
        if not api_key:
            return {'valid': False, 'error': '请提供API密钥'}
        
        # 验证API密钥格式
        import re
        if not re.match(r'^xai-[A-Za-z0-9]{50,}$', api_key):
            return {'valid': False, 'error': 'API密钥格式不正确'}
        
        # 使用requests库测试API密钥
        import requests
        from urllib.parse import urlparse
        
        url = API_URL
        parsed_url = urlparse(url)
        hostname = parsed_url.netloc
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'Grok-API-Client/1.0',
            'Host': 'api.x.ai'  # 确保请求发送到正确的主机名
        }
        
        data_payload = {
            'messages': [{'role': 'user', 'content': 'Hi'}],
            'model': os.getenv('MODEL_NAME', 'grok-3-fast-latest'),
            'max_tokens': 1
        }
        
        # 检查是否在Render环境中
        is_render = os.environ.get('RENDER', '').lower() == 'true'
        api_request_url = url
        
        # 在Render环境中尝试IP直连
        if is_render:
            logger.info(f"API验证: 在Render环境中，尝试IP直连")
            
            # 如果提供了备用IP地址，使用IP直连
            if API_IP:
                # 构建IP直连URL
                scheme = parsed_url.scheme
                path = parsed_url.path
                ip_url = f"{scheme}://{API_IP}{path}"
                logger.info(f"API验证: 使用IP直连: {ip_url}")
                api_request_url = ip_url
            else:
                # 尝试手动解析域名
                resolved_ip = resolve_hostname(hostname)
                if resolved_ip:
                    logger.info(f"API验证: 成功解析域名 {hostname} 为 {resolved_ip}")
                    scheme = parsed_url.scheme
                    path = parsed_url.path
                    ip_url = f"{scheme}://{resolved_ip}{path}"
                    logger.info(f"API验证: 使用解析的IP: {ip_url}")
                    api_request_url = ip_url
        
        try:
            # 创建带自定义SSL上下文的会话
            try:
                session = requests.Session()
                
                # 直接创建适配器并设置SSL上下文
                from requests.adapters import HTTPAdapter
                from urllib3.poolmanager import PoolManager
                
                class CustomSSLAdapter(HTTPAdapter):
                    def init_poolmanager(self, connections, maxsize, block=False):
                        self.poolmanager = PoolManager(
                            num_pools=connections,
                            maxsize=maxsize,
                            block=block,
                            ssl_version=ssl.PROTOCOL_TLS_CLIENT,
                            ssl_context=ssl_context
                        )
                
                # 为http和https设置适配器
                adapter = CustomSSLAdapter()
                session.mount('https://', adapter)
                session.mount('http://', adapter)
                
                logger.debug(f"API验证: 创建了自定义SSL会话")
                
            except Exception as e:
                logger.warning(f"API验证: 无法创建自定义SSL会话: {str(e)}, 使用标准会话")
                session = requests.Session()
            
            # 设置会话不验证SSL
            session.verify = False
            
            # 使用会话发送请求
            response = session.post(
                api_request_url, 
                headers=headers, 
                json=data_payload, 
                timeout=10
            )
            
            if response.status_code == 200:
                return {'valid': True, 'message': 'API密钥验证成功'}
            elif response.status_code == 401:
                return {'valid': False, 'error': 'API密钥无效或已过期'}
            elif response.status_code == 403:
                return {'valid': False, 'error': 'API访问被拒绝，请检查密钥权限'}
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', f'API请求失败: {response.status_code}')
                except:
                    error_msg = f'API请求失败: {response.status_code}'
                return {'valid': False, 'error': error_msg}
        
        except RecursionError as e:
            logger.error(f"API验证: 递归错误: {str(e)}")
            
            # 尝试使用低级HTTP客户端作为后备方案
            try:
                logger.info(f"API验证: 尝试使用http.client作为后备方案")
                
                # 获取主机和路径
                parsed_url = urlparse(api_request_url)
                host = parsed_url.netloc
                path = parsed_url.path or '/'
                
                # 准备JSON数据
                import json
                json_data = json.dumps(data_payload).encode('utf-8')
                
                # 建立连接
                conn = None
                try:
                    # 检查URL是否为HTTPS
                    is_https = parsed_url.scheme.lower() == 'https'
                    port = 443 if is_https else 80
                    
                    # 使用基本HTTP连接，但设置正确的端口
                    logger.debug(f"API验证: 使用HTTP连接到 {host}:{port}")
                    conn = http.client.HTTPConnection(host, port, timeout=10)
                    
                    # 添加额外的请求头，以处理HTTPS请求
                    if is_https:
                        headers = dict(headers)  # 创建副本以避免修改原始字典
                        headers['X-Forwarded-Proto'] = 'https'
                    
                    # 发送请求
                    logger.debug(f"API验证: 使用http.client发送请求")
                    conn.request(
                        "POST", 
                        path, 
                        body=json_data, 
                        headers=headers
                    )
                    
                    # 获取响应
                    http_response = conn.getresponse()
                    
                    if http_response.status == 200:
                        return {'valid': True, 'message': 'API密钥验证成功 (通过后备方法)'}
                    elif http_response.status == 401:
                        return {'valid': False, 'error': 'API密钥无效或已过期'}
                    elif http_response.status == 403:
                        return {'valid': False, 'error': 'API访问被拒绝，请检查密钥权限'}
                    else:
                        return {'valid': False, 'error': f'API请求失败: {http_response.status}'}
                
                except http.client.HTTPException as he:
                    logger.error(f"API验证: HTTP客户端异常: {str(he)}")
                    return {'valid': False, 'error': f'HTTP连接错误: {str(he)}'}
                except socket.error as se:
                    logger.error(f"API验证: 套接字错误: {str(se)}")
                    return {'valid': False, 'error': f'网络连接错误: {str(se)}'}
                except Exception as conn_error:
                    logger.error(f"API验证: 连接错误: {str(conn_error)}")
                    return {'valid': False, 'error': f'连接错误: {str(conn_error)}'}
                finally:
                    # 确保连接被关闭
                    if conn:
                        try:
                            conn.close()
                        except:
                            pass
                    
            except Exception as backup_error:
                logger.error(f"API验证: 后备方案失败: {str(backup_error)}")
                import traceback
                logger.error(f"API验证: 错误详情: {traceback.format_exc()}")
                return {'valid': False, 'error': 'SSL验证错误，无法连接到API服务器'}
                
        except requests.exceptions.Timeout:
            return {'valid': False, 'error': '请求超时，请检查网络连接'}
        except requests.exceptions.ConnectionError:
            return {'valid': False, 'error': '网络连接失败，请检查网络设置或稍后再试'}
        except Exception as e:
            return {'valid': False, 'error': f'请求错误: {str(e)}'}
            
    except Exception as e:
        logger.error(f"API密钥验证错误: {str(e)}")
        return {'valid': False, 'error': '验证过程中发生错误'}

@socketio.on('get_history')
def get_history():
    socketio.emit('update_history', {
        'conversations': [
            {
                'id': cid,
                'title': conv['title'],
                'timestamp': conv['timestamp']
            } for cid, conv in conversation_history.items()
        ]
    })

@socketio.on('get_conversation')
def get_conversation(data):
    conversation_id = data['conversation_id']
    if conversation_id in conversation_history:
        socketio.emit('load_conversation', {
            'messages': conversation_history[conversation_id]['messages']
        })

@socketio.on('new_conversation')
def handle_new_conversation():
    # Reset session ID
    session['conversation_id'] = datetime.now().strftime('%Y%m%d%H%M%S')
    # Clear current session history
    conversation_id = session.get('conversation_id')
    if conversation_id in conversation_history:
        del conversation_history[conversation_id]
    # Notify client that reset is complete
    socketio.emit('conversation_reset')

@socketio.on('delete_conversation')
def handle_delete_conversation(data):
    conversation_id = data['conversation_id']
    if conversation_id in conversation_history:
        del conversation_history[conversation_id]
        # Send updated history
        socketio.emit('update_history', {
            'conversations': [
                {
                    'id': cid,
                    'title': conv['title'],
                    'timestamp': conv['timestamp']
                } for cid, conv in conversation_history.items()
            ]
        })

@socketio.on('send_message')
def handle_message(data):
    # 添加请求ID用于跟踪
    request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(str(data))}"
    logger.info(f'Processing message request [ID:{request_id}]')
    
    try:
        # Basic validation
        if not data.get('message'):
            logger.error(f'[ID:{request_id}] Message content is empty')
            socketio.emit('error', {'message': 'Message content cannot be empty'}, room=request.sid)
            return

        # Check conversation ID
        conversation_id = get_conversation_id()
        logger.debug(f'[ID:{request_id}] Conversation ID: {conversation_id}')
        
        # Check API key
        api_key = data.get('api_key') or user_api_keys.get(request.sid)
        if not api_key:
            logger.error(f'[ID:{request_id}] API key not set')
            socketio.emit('error', {'message': 'Please set your API key first'}, room=request.sid)
            return

        # Log key request info
        logger.debug(f'[ID:{request_id}] API URL: {API_URL}')
        logger.debug(f'[ID:{request_id}] Message length: {len(data.get("message", ""))} characters')
        
        # Update API key
        user_api_keys[request.sid] = api_key
        
        # Handle Live Search settings
        if 'live_search_enabled' in data:
            user_live_search_settings[request.sid] = data.get('live_search_enabled')

        # Message length check
        if len(data.get('message', '')) > 4000:
            logger.warning(f'[ID:{request_id}] Message too long: {len(data.get("message", ""))} characters')
            socketio.emit('error', {'message': 'Message is too long, please shorten your message'}, room=request.sid)
            return

        # Build user message
        user_message = {
            'role': 'user',
            'content': data['message'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Get current conversation messages
        current_messages = []
        try:
            logger.debug(f'[ID:{request_id}] Attempting to get conversation messages')
            current_messages = list(session_manager.get_conversation_messages(conversation_id))
            logger.debug(f'[ID:{request_id}] Current conversation message count: {len(current_messages)}')
        except Exception as e:
            error_trace = log_exception(e, f'[ID:{request_id}] Failed to get conversation messages')
            # Continue processing, use empty list
            current_messages = []

        # Add user message
        try:
            logger.debug(f'[ID:{request_id}] Attempting to add user message to conversation')
            session_manager.add_message_to_conversation(conversation_id, user_message)
            logger.debug(f'[ID:{request_id}] User message added to conversation')
        except Exception as e:
            error_trace = log_exception(e, f'[ID:{request_id}] Failed to add user message')
            socketio.emit('error', {
                'message': 'Error processing message, please try again', 
                'request_id': request_id
            }, room=request.sid)
            return

        # Send processing confirmation
        socketio.emit('message_received', {
            'status': 'processing',
                    'request_id': request_id
                }, room=request.sid)

        # Build system message
        system_message = 'You are a helpful assistant.'
        logger.debug(f'[ID:{request_id}] Using default system message')

        # Build API request message list - Fix the logic here to ensure messages are added in the correct order
        messages = [{'role': 'system', 'content': system_message}]
        
        # If there are existing conversation messages, add them after the system message
        if current_messages:
            messages.extend(current_messages)
        
        # Don't need to add the user message that's already been added to the conversation history
        # Check if the last message is already the current user message
        if not messages or messages[-1]['role'] != 'user' or messages[-1]['content'] != user_message['content']:
            messages.append(user_message)
            
        logger.debug(f'[ID:{request_id}] Ready to send API request, total messages: {len(messages)}, including system message: {system_message[:50]}...')

        # Call API
        try:
            logger.debug(f'[ID:{request_id}] Starting API call')
            response_data = send_message(messages, api_key, user_live_search_settings.get(request.sid, False))
            logger.debug(f'[ID:{request_id}] API call completed, checking response')
        except Exception as e:
            error_trace = log_exception(e, f'[ID:{request_id}] API call failed')
            socketio.emit('error', {
                'message': 'API call failed, please try again later',
                'request_id': request_id
            }, room=request.sid)
            return

        # Check for error response
        if 'error' in response_data:
            logger.error(f'[ID:{request_id}] API returned error: {response_data["error"]}')
            socketio.emit('error', {
                'message': response_data['error'],
                'request_id': request_id
            }, room=request.sid)
            return

        # Validate response format
        if not (response_data and 'response' in response_data and 'choices' in response_data['response']):
            logger.error(f'[ID:{request_id}] API response format does not match expected: {json.dumps(response_data)}')
            socketio.emit('error', {
                'message': 'API response format error',
                'request_id': request_id
            }, room=request.sid)
            return

        # Process API response
        try:
            # Extract assistant reply
            choices = response_data['response']['choices']
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                logger.error(f'[ID:{request_id}] API response choices empty or format error')
                socketio.emit('error', {
                    'message': 'Incomplete API response data',
                    'request_id': request_id
                }, room=request.sid)
                return

            # Check message format
            first_choice = choices[0]
            if not isinstance(first_choice, dict) or 'message' not in first_choice:
                logger.error(f'[ID:{request_id}] API response choice format error: {json.dumps(first_choice)}')
                socketio.emit('error', {
                    'message': 'API response data format error',
                    'request_id': request_id
                }, room=request.sid)
                return

            # Extract message content
            message_obj = first_choice['message']
            if not isinstance(message_obj, dict) or 'content' not in message_obj:
                logger.error(f'[ID:{request_id}] API response message format error: {json.dumps(message_obj)}')
                socketio.emit('error', {
                    'message': 'API response message format error',
                    'request_id': request_id
                }, room=request.sid)
                return

            # Get content
            assistant_message = message_obj['content']
            logger.debug(f'[ID:{request_id}] Successfully extracted assistant reply, length: {len(assistant_message)} characters')
            
            # Build assistant message object
            assistant_message_obj = {
                'role': 'assistant',
                'content': assistant_message,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Add assistant message to conversation
            try:
                logger.debug(f'[ID:{request_id}] Attempting to add assistant reply to conversation')
                session_manager.add_message_to_conversation(conversation_id, assistant_message_obj)
                logger.debug(f'[ID:{request_id}] Assistant reply added to conversation')
            except Exception as e:
                error_trace = log_exception(e, f'[ID:{request_id}] Failed to add assistant reply to conversation')
                # Try to return response to user even if adding to conversation fails

            # Send response to client
            logger.debug(f'[ID:{request_id}] Sending response to client')
            socketio.emit('response', {
                'message': assistant_message,
                'conversation_id': conversation_id,
                'response_time': round(response_data.get('response_time', 0), 2),
                'token_count': response_data.get('token_count', 0),
                'request_id': request_id
            }, room=request.sid)

            # Update conversation list
            try:
                logger.debug(f'[ID:{request_id}] Updating conversation list')
                conversations = [
                    {
                        'id': cid,
                        'title': conv['title'],
                        'timestamp': conv['timestamp']
                    } for cid, conv in session_manager.conversation_history.items()
                ]
                socketio.emit('update_history', {'conversations': conversations}, room=request.sid)
                logger.info(f'[ID:{request_id}] Message processing completed')
            except Exception as e:
                error_trace = log_exception(e, f'[ID:{request_id}] Failed to update conversation list')
                # Don't block main functionality

        except Exception as e:
            error_trace = log_exception(e, f'[ID:{request_id}] Failed to process API response')
            socketio.emit('error', {
                'message': 'Error processing response, please try again',
                'request_id': request_id
            }, room=request.sid)
            return

    except Exception as e:
        error_trace = log_exception(e, f'[ID:{request_id}] Error in main message processing flow')
        socketio.emit('error', {
            'message': f'An unknown error occurred, please try again later',
            'request_id': request_id
        }, room=request.sid)

@socketio.on('update_settings')
def handle_update_settings(data):
    """处理用户设置更新事件"""
    session_id = request.sid
    logger.debug(f"接收到设置更新请求: session_id={session_id}")
    
    # 更新API密钥
    if 'api_key' in data and data['api_key']:
        # 安全地记录日志，不显示完整API密钥
        masked_key = data['api_key'][:5] + "..." + data['api_key'][-3:] if len(data['api_key']) > 8 else "***"
        logger.debug(f"为会话 {session_id} 更新API密钥: {masked_key}")
        user_api_keys[session_id] = data['api_key']
    
    # 更新实时搜索设置
    if 'live_search_enabled' in data:
        logger.debug(f"为会话 {session_id} 更新实时搜索设置: {data['live_search_enabled']}")
        user_live_search_settings[session_id] = data['live_search_enabled']
    
    socketio.emit('settings_updated', {'success': True}, room=session_id)
    logger.debug(f"设置更新完成: session_id={session_id}")

@app.route('/socket-test')
def socket_test():
    """WebSocket连接测试页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket测试</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    </head>
    <body>
        <h1>WebSocket连接测试</h1>
        <div id="status">正在连接...</div>
        <script>
            const status = document.getElementById('status');
            const socket = io(window.location.origin, {
                path: '/socket.io',
                transports: ['polling', 'websocket'],
                upgrade: true
            });
            
            socket.on('connect', () => {
                status.textContent = '✅ 连接成功！Socket ID: ' + socket.id;
                status.style.color = 'green';
            });
            
            socket.on('connect_error', (error) => {
                status.textContent = '❌ 连接失败: ' + error.message;
                status.style.color = 'red';
                console.error('连接错误:', error);
            });
            
            socket.on('disconnect', (reason) => {
                status.textContent = '❌ 连接断开: ' + reason;
                status.style.color = 'orange';
            });
        </script>
    </body>
    </html>
    """

@socketio.on('ping_test')
def handle_ping_test():
    """处理WebSocket ping测试"""
    logger.debug(f"收到ping_test请求: session_id={request.sid}")
    socketio.emit('pong_test', {'success': True, 'timestamp': datetime.now().isoformat()}, room=request.sid)

if __name__ == '__main__':
    # Start cleanup task
    from threading import Thread
    cleanup_thread = Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()
    
    # Get port from environment variables, adapt to cloud platform requirements
    port = int(os.getenv('PORT', 10000))
    host = os.getenv('HOST', '0.0.0.0')
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Log startup information
    logger.info(f"🚀 Grok 3.0 Chat Application Starting...")
    logger.info(f"📡 Server: {host}:{port}")
    logger.info(f"🔗 API URL: {API_URL}")
    logger.info(f"🤖 Model: {os.getenv('MODEL_NAME', 'grok-3-fast-latest')}")
    logger.info(f"🔧 Debug Mode: {debug_mode}")
    logger.info(f"💾 Max Conversations: {session_manager.max_conversations}")
    logger.info(f"💬 Max Messages per Conversation: {session_manager.max_messages_per_conversation}")
    logger.info(f"🔍 Live Search: Integrated with xAI API")
    
    # In cloud environments, host and port are usually automatically assigned
    if os.environ.get('RENDER', '') == 'true':
        # When running on Render, the app is started by gunicorn
        # socketio configuration is handled by gunicorn settings
        logger.info("Running on Render, letting gunicorn handle the app")
    else:
        # For local development, start the app directly
        try:
            socketio.run(
                app, 
                host=host, 
                port=port,
                debug=debug_mode,
                use_reloader=False,  # Disable reloader for production
                log_output=debug_mode  # Only log output in debug mode
            )
        except Exception as e:
            logger.error(f"❌ Failed to start server: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            exit(1)