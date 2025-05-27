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
    # Create custom SSL context that doesn't verify certificates
    # This helps avoid SSL recursion errors in Python's SSL module
    ssl._create_default_https_context = ssl._create_unverified_context
    logger.debug("Custom SSL context set")
    
    # Import and configure urllib3 to ignore SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.debug("urllib3 warnings disabled")
    
    # Patch requests session to bypass SSL verification
    # This prevents recursion errors in the requests library's SSL handling
    old_merge_environment_settings = requests.Session.merge_environment_settings
    
    def patched_merge_environment_settings(self, url, proxies, stream, verify, cert):
        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False
        return settings
    
    requests.Session.merge_environment_settings = patched_merge_environment_settings
    logger.debug("Requests session settings patched")
    
    # Disable SSL warnings at package level
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
    cors_allowed_origins="*",  # Allow cross-origin requests
    ping_timeout=60,          # Reduce timeout for better cloud compatibility
    ping_interval=25,         # Increase ping interval for cloud stability
    async_mode='threading',   # Use threading for better compatibility
    logger=False,             # Disable SocketIO logging in production
    engineio_logger=False     # Disable Engine.IO logging in production
)

# API endpoint for Grok API
API_URL = os.getenv('API_URL', 'https://api.x.ai/v1/chat/completions')

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
        return {'error': '请先在设置中配置有效的API密钥'}

    # 配置重试策略
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import socket
    from urllib3.exceptions import MaxRetryError, NameResolutionError

    # 创建自定义的 Session
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=3,  # 最大重试次数
        backoff_factor=1,  # 重试间隔
        status_forcelist=[500, 502, 503, 504],  # 需要重试的HTTP状态码
        allowed_methods=["POST"],  # 允许重试的HTTP方法
        respect_retry_after_header=True
    )
    
    # 配置适配器
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        # 验证消息格式
        if not isinstance(messages, list):
            logger.error("Invalid message format: not a list")
            return {'error': '无效的消息格式'}

        for msg in messages:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                logger.error("Invalid message format: missing required fields")
                return {'error': '无效的消息格式'}

        # 记录请求详情
        request_id = datetime.now().strftime('%Y%m%d%H%M%S')
        logger.debug(f"API request[{request_id}] initializing: message count={len(messages)}")
        logger.debug(f"API request[{request_id}] URL: {API_URL}")

        # 从环境变量获取模型信息
        model = os.getenv('MODEL_NAME', 'grok-3-fast-latest')
        temperature = float(os.getenv('TEMPERATURE', '0'))
        logger.debug(f"API request[{request_id}] model: {model}, temperature: {temperature}")

        # 构建请求数据
        data = {
            'messages': messages,
            'model': model,
            'stream': False,
            'temperature': temperature
        }

        # 如果启用Live Search，添加搜索参数
        if enable_live_search:
            data['search_parameters'] = {
                'mode': 'auto',
                'max_search_results': 5,
                'time_range': '24h'
            }
            logger.debug(f"API request[{request_id}] Live Search enabled")

        # 构建请求头
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'Grok-API-Client/1.0'
        }

        start_time = datetime.now()

        try:
            # 使用配置好的session发送请求
            logger.debug(f"API request[{request_id}] sending request to {API_URL}")
            response = session.post(
                API_URL,
                json=data,
                headers=headers,
                timeout=30,
                verify=False  # 禁用SSL验证以避免问题
            )

            response_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"API request[{request_id}] response status: {response.status_code}, time: {response_time}s")

            # 检查响应状态
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        message = result['choices'][0]['message']['content']
                        token_count = result.get('usage', {}).get('total_tokens', 0)
                        return {
                            'message': message,
                            'response_time': round(response_time, 2),
                            'token_count': token_count,
                            'request_id': request_id
                        }
                    else:
                        logger.error(f"API request[{request_id}] invalid response format")
                        return {'error': 'API返回格式无效'}
                except json.JSONDecodeError as e:
                    logger.error(f"API request[{request_id}] JSON decode error: {str(e)}")
                    return {'error': '无法解析API响应'}
            else:
                error_msg = f"API request[{request_id}] failed with status {response.status_code}"
                try:
                    error_detail = response.json().get('error', {}).get('message', 'Unknown error')
                    error_msg += f": {error_detail}"
                except:
                    pass
                logger.error(error_msg)
                return {'error': f'API请求失败 (状态码: {response.status_code})'}

        except (requests.exceptions.ConnectionError, MaxRetryError, NameResolutionError) as e:
            logger.error(f"API request[{request_id}] connection error: {str(e)}")
            if isinstance(e, NameResolutionError):
                return {'error': '无法解析API服务器地址，请检查网络连接或DNS设置'}
            return {'error': '网络连接失败，请检查您的网络连接'}
        except requests.exceptions.Timeout:
            logger.error(f"API request[{request_id}] request timeout")
            return {'error': '请求超时，请稍后重试'}
        except requests.exceptions.RequestException as e:
            logger.error(f"API request[{request_id}] request error: {str(e)}")
            return {'error': f'请求错误: {str(e)}'}

    except Exception as e:
        logger.error(f"API request[{request_id}] unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'error': '发生意外错误，请稍后重试'}

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
        
        url = API_URL
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'Grok-API-Client/1.0'
        }
        
        data_payload = {
            'messages': [{'role': 'user', 'content': 'Hi'}],
            'model': os.getenv('MODEL_NAME', 'grok-3-fast-latest'),
            'max_tokens': 1
        }
        
        try:
            response = requests.post(url, headers=headers, json=data_payload, timeout=10, verify=False)
            
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
                
        except requests.exceptions.Timeout:
            return {'valid': False, 'error': '请求超时，请检查网络连接'}
        except requests.exceptions.ConnectionError:
            return {'valid': False, 'error': '网络连接失败，请检查网络设置'}
    except Exception as e:
        return {'valid': False, 'error': f'请求错误: {str(e)}'}

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
    
    try:
        # In cloud environments, host and port are usually automatically assigned
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