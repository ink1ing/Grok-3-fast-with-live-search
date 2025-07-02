#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import socket
from urllib.parse import urlparse

def dns_precheck(hostname):
    """DNS预检查，确保域名可以解析"""
    try:
        result = socket.gethostbyname(hostname)
        print(f"✅ DNS解析成功: {hostname} -> {result}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS解析失败: {hostname} - {e}")
        return False
    except Exception as e:
        print(f"❌ DNS解析异常: {hostname} - {e}")
        return False

def test_api_url_parsing():
    """测试API URL解析"""
    # 获取API_URL
    API_URL = os.getenv('API_URL', 'https://api.x.ai/v1/chat/completions')
    print(f"🔗 API_URL: {API_URL}")
    
    # 解析URL
    try:
        parsed_url = urlparse(API_URL)
        hostname = parsed_url.hostname
        print(f"🏠 解析出的主机名: {hostname}")
        
        # 测试DNS解析
        dns_result = dns_precheck(hostname)
        
        return dns_result
    except Exception as e:
        print(f"❌ URL解析失败: {e}")
        return False

if __name__ == '__main__':
    print("=== DNS调试测试 ===")
    print()
    
    # 测试API URL解析和DNS
    result = test_api_url_parsing()
    print()
    
    if result:
        print("✅ 所有测试通过")
    else:
        print("❌ 测试失败")
    
    print()
    print("=== 额外测试 ===")
    
    # 直接测试api.x.ai
    print("直接测试 api.x.ai:")
    dns_precheck('api.x.ai')
    
    # 测试其他域名
    print("\n测试 google.com:")
    dns_precheck('google.com')