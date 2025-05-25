#!/usr/bin/env python3
"""
测试SSL修复是否有效的脚本
运行方式: python test_ssl_fix.py
"""

import os
import ssl
import json
import http.client
import urllib3
import requests
from urllib.parse import urlparse
import logging
import sys
import time

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SSL_TEST")

# 测试URL
TEST_URL = os.getenv('API_URL', 'https://api.x.ai/v1/chat/completions')
# 备用IP
TEST_IP = os.getenv('API_IP', '146.75.33.95')

def test_ssl_fix():
    """测试SSL修复是否有效"""
    logger.info("开始SSL修复测试...")
    
    # 1. 创建自定义SSL上下文
    try:
        logger.info("1. 创建自定义SSL上下文")
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
        logger.info("✓ 自定义SSL上下文创建成功")
    except Exception as e:
        logger.error(f"✗ 自定义SSL上下文创建失败: {str(e)}")
        return False
    
    # 2. 测试requests + 自定义适配器
    try:
        logger.info("2. 测试requests库 + 自定义适配器")
        # 创建自定义适配器
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
        
        # 创建会话并设置适配器
        session = requests.Session()
        adapter = CustomSSLAdapter()
        session.mount('https://', adapter)
        session.verify = False
        
        # 解析URL
        parsed_url = urlparse(TEST_URL)
        hostname = parsed_url.netloc
        
        # 准备测试直接通过域名访问
        logger.info(f"2.1 通过域名访问 {hostname}")
        try:
            response = session.get(
                f"https://{hostname}", 
                timeout=5,
                headers={'User-Agent': 'SSL-Fix-Test/1.0', 'Host': hostname}
            )
            logger.info(f"✓ 域名访问成功: 状态码 {response.status_code}")
        except Exception as e:
            logger.warning(f"✗ 域名访问失败: {str(e)}")
            logger.info("这可能是网络限制导致的，不一定是SSL问题")
        
        # 准备测试通过IP直连访问
        if TEST_IP:
            logger.info(f"2.2 通过IP直连访问 {TEST_IP}")
            try:
                response = session.get(
                    f"https://{TEST_IP}", 
                    timeout=5,
                    headers={'User-Agent': 'SSL-Fix-Test/1.0', 'Host': hostname}
                )
                logger.info(f"✓ IP直连访问成功: 状态码 {response.status_code}")
            except Exception as e:
                logger.warning(f"✗ IP直连访问失败: {str(e)}")
                logger.info("这可能是由于服务器要求SNI，但不一定是SSL递归问题")
        
        logger.info("✓ requests库测试完成")
    except RecursionError as e:
        logger.error(f"✗ requests库测试失败，出现递归错误: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ requests库测试过程中出现其他错误: {str(e)}")
        # 继续执行其他测试
    
    # 3. 测试http.client
    try:
        logger.info("3. 测试http.client库 (低级HTTP客户端)")
        
        # 通过域名访问
        logger.info(f"3.1 通过域名访问 {hostname}")
        try:
            conn = http.client.HTTPSConnection(hostname, context=ssl_context, timeout=5)
            conn.request("GET", "/", headers={'User-Agent': 'SSL-Fix-Test/1.0'})
            response = conn.getresponse()
            logger.info(f"✓ 域名访问成功: 状态码 {response.status}")
            conn.close()
        except Exception as e:
            logger.warning(f"✗ 域名访问失败: {str(e)}")
            logger.info("这可能是网络限制导致的，不一定是SSL问题")
        
        # 通过IP直连访问
        if TEST_IP:
            logger.info(f"3.2 通过IP直连访问 {TEST_IP}")
            try:
                conn = http.client.HTTPSConnection(TEST_IP, context=ssl_context, timeout=5)
                conn.request("GET", "/", headers={'User-Agent': 'SSL-Fix-Test/1.0', 'Host': hostname})
                response = conn.getresponse()
                logger.info(f"✓ IP直连访问成功: 状态码 {response.status}")
                conn.close()
            except Exception as e:
                logger.warning(f"✗ IP直连访问失败: {str(e)}")
                logger.info("这可能是由于服务器要求SNI，但不一定是SSL递归问题")
        
        logger.info("✓ http.client库测试完成")
    except Exception as e:
        logger.error(f"✗ http.client库测试失败: {str(e)}")
        # 继续执行其他测试
    
    # 测试结论
    logger.info("SSL修复测试完成!")
    logger.info("如果没有看到递归错误信息，则SSL修复方案有效")
    return True

if __name__ == "__main__":
    try:
        # 先禁用urllib3警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 运行测试
        test_ssl_fix()
        
        logger.info("")
        logger.info("=== 测试DNS解析功能 ===")
        hostname = urlparse(TEST_URL).netloc
        
        # 使用socket测试DNS解析
        try:
            import socket
            logger.info(f"使用socket.gethostbyname解析 {hostname}")
            ip = socket.gethostbyname(hostname)
            logger.info(f"✓ 解析成功: {hostname} -> {ip}")
        except Exception as e:
            logger.error(f"✗ 解析失败: {str(e)}")
        
        # 使用dnspython测试DNS解析
        try:
            import dns.resolver
            logger.info(f"使用dnspython解析 {hostname}")
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '1.1.1.1']
            answers = resolver.resolve(hostname, 'A')
            for rdata in answers:
                logger.info(f"✓ 解析成功: {hostname} -> {str(rdata)}")
        except ImportError:
            logger.warning("✗ dnspython未安装，无法测试")
        except Exception as e:
            logger.error(f"✗ 解析失败: {str(e)}")
            
    except Exception as e:
        logger.error(f"测试过程中出现未捕获的异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1) 