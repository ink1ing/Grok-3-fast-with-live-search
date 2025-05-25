# Render部署DNS问题修复

## 问题描述

Render环境中出现DNS解析问题，无法访问`api.x.ai`域名，导致API调用失败：

```
Error: Network connection failed, please check your internet connection
```

日志中显示：
```
HTTPSConnectionPool(host='api.x.ai', port=443): Max retries exceeded with url: /v1/chat/completions (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x778b864bd6d0>: Failed to resolve 'api.x.ai' ([Errno -3] Lookup timed out)"))
```

## SSL递归错误问题

另一个常见问题是SSL递归错误：

```
RecursionError: maximum recursion depth exceeded while calling a Python object
```

这是Python的SSL模块中的一个已知问题，特别是在使用requests库与TLS连接时。

## 解决方案

### DNS解析问题解决方案

1. **IP直连模式**：
   - 添加了`API_IP`环境变量，配置为`api.x.ai`的IP地址
   - 当DNS解析失败时，自动切换到IP直连模式
   - 在请求头中保留`Host: api.x.ai`确保API服务器正确处理请求

2. **自定义DNS解析器**：
   - 添加了`dnspython`库，使用自定义DNS解析器
   - 配置使用Google DNS (8.8.8.8) 和Cloudflare DNS (1.1.1.1)
   - 添加`DNS_SERVERS`环境变量，可自定义DNS服务器

3. **重试机制**：
   - 添加了网络请求重试机制，最多重试3次
   - 在重试过程中自动切换到IP直连模式
   - 增加了详细的日志记录，便于诊断

### SSL递归错误解决方案

1. **自定义SSL上下文**：
   - 创建一个全局的SSL上下文，不进行证书验证
   - 设置宽松的密码套件，避免SSL验证问题
   - 禁用主机名验证，确保IP直连可以正常工作

2. **HTTP适配器注入**：
   - 为requests会话创建自定义HTTP适配器
   - 直接注入自定义SSL上下文到底层连接池
   - 避免使用默认的SSL上下文创建方法，防止递归

3. **备用HTTP客户端**：
   - 当检测到递归错误时，自动切换到低级http.client库
   - 绕过requests库的SSL处理层，直接使用Python内置HTTP客户端
   - 确保即使在极端情况下也能完成API调用

4. **多层错误处理**：
   - 专门捕获并处理RecursionError异常
   - 增强日志记录，帮助诊断SSL相关问题
   - 优化错误消息，提供更友好的用户体验

## 部署说明

1. 确保render.yaml包含以下环境变量：
   ```yaml
   - key: API_IP
     value: "146.75.33.95"
   - key: DNS_SERVERS
     value: "8.8.8.8,8.8.4.4,1.1.1.1"
   - key: EVENTLET_NO_GREENDNS
     value: "yes"
   ```

2. 确保requirements.txt包含：
   ```
   dnspython==2.4.2
   ```

3. 如果将来`api.x.ai`的IP地址变更，只需要更新`API_IP`环境变量即可

## 验证方法

1. 访问应用的`/health`端点，确保应用正常运行
2. 访问`/socket-test`页面，测试WebSocket连接是否正常
3. 在聊天界面输入消息，验证API连接是否成功
4. 检查日志中是否还有递归错误或DNS解析错误

## 未来维护

如果API域名或IP地址发生变化，请更新以下内容：

1. render.yaml中的`API_URL`和`API_IP`环境变量
2. 重新部署应用

## 技术说明

这个解决方案使用了以下技术：

1. DNS手动解析 - 使用dnspython库或socket.gethostbyname
2. HTTP头部修改 - 使用Host头确保API服务器识别请求
3. 网络重试策略 - 包括错误检测和备用方案
4. 环境检测 - 识别Render环境并应用特定配置
5. 自定义SSL上下文 - 避免Python SSL模块中的递归问题
6. HTTP适配器注入 - 绕过requests的默认SSL处理
7. 多层错误处理 - 确保应用在各种网络条件下都能正常工作 