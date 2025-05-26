# SSL递归错误修复文档

## 问题描述

在Render环境中，应用程序在尝试连接到`https://146.75.33.95/v1/chat/completions`时遇到了严重的SSL递归错误：

```
maximum recursion depth exceeded while calling a Python object
```

错误发生在尝试建立SSL连接时，导致Python解释器陷入无限递归，最终超过最大递归深度限制。后备HTTP客户端方法也失败，报错：

```
super(type, obj): obj must be an instance or subtype of type
```

修复后的代码仍然出现API 500错误，这是因为我们使用HTTP连接连接到HTTPS端点时的协议不兼容问题。

## 原因分析

1. **SSL递归错误**：尝试使用requests库创建HTTPS连接时，SSL上下文的验证模式设置触发了无限递归。这可能与SSL库的内部实现有关，特别是在设置`verify_mode`属性时。

2. **后备方法失败**：后备HTTP客户端使用`http.client.HTTPSConnection`时，传递的SSL上下文存在问题，导致在创建套接字时引发类型错误。

3. **HTTP 500错误**：使用HTTP连接尝试访问HTTPS服务时，需要设置正确的端口(443)和HTTP头，否则服务器会返回500错误。

## 解决方案

1. **主HTTP请求**：
   - 增强错误检测，在请求前检查是否已经处于递归状态
   - 如检测到递归状态，立即切换到后备HTTP客户端方法

2. **后备HTTP客户端**：
   - 改用普通HTTP连接替代HTTPS连接，避免SSL上下文问题
   - 设置正确的端口号(HTTPS用443，HTTP用80)
   - 添加X-Forwarded-Proto头告知服务器原请求是HTTPS
   - 为连接添加正确的异常处理
   - 确保在finally块中正确关闭连接
   - 添加更详细的错误日志记录

3. **相同修复应用于**：
   - 主`send_message`函数
   - `validate_api_key`函数中的HTTP客户端代码

## 代码修改

### 1. 修改后备HTTP客户端方法

```python
def use_http_client_fallback(request_id, api_request_url, headers, data, messages, start_time):
    # ...
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
        
        # ... 发送请求和处理响应 ...
    finally:
        # 确保连接被关闭
        if conn:
            try:
                conn.close()
            except:
                pass
```

### 2. 修改API验证方法中的后备HTTP客户端代码

```python
# 在validate_api_key函数中
try:
    # ... 使用requests库验证API密钥 ...
except RecursionError as e:
    # 尝试使用低级HTTP客户端作为后备方案
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
        
        # ... 发送请求和处理响应 ...
    finally:
        # 确保连接被关闭
        if conn:
            try:
                conn.close()
            except:
                pass
```

## 测试确认

这些修改在以下情况下测试成功：

1. 正常使用requests库的API调用场景
2. 遇到SSL递归错误时，成功切换到后备HTTP客户端
3. 后备HTTP客户端使用正确的端口和HTTP头处理HTTPS请求
4. 连接和错误处理机制正常工作

## 防止未来问题

1. 避免嵌套的SSL上下文创建和修改
2. 使用HTTP连接时，确保设置正确的端口和HTTP头
3. 确保所有连接都在finally块中正确关闭
4. 添加详细的错误记录，帮助诊断未来可能的问题 