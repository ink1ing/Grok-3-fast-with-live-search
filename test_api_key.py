#!/usr/bin/env python3
"""
测试xAI API密钥的有效性
"""
import requests
import json
import sys
import re

def test_api_key(api_key):
    """测试API密钥是否有效"""
    
    # 只显示密钥的一部分，保护隐私
    if len(api_key) > 20:
        masked_key = f"{api_key[:10]}...{api_key[-4:]}"
    else:
        masked_key = "[密钥格式不正确]"
        
    print(f"🔑 测试API密钥: {masked_key}")
    
    # 构建请求
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    data = {
        "model": "grok-3-fast-latest",
        "messages": [
            {"role": "user", "content": "Hi"}
        ],
        "max_tokens": 1
    }
    
    try:
        print("📡 发送测试请求...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API密钥验证成功！")
            response_data = response.json()
            print(f"📝 响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            return True
        else:
            print("❌ API密钥验证失败")
            try:
                error_data = response.json()
                print(f"🚨 错误信息: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"🚨 错误信息: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ 请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("🌐 网络连接错误")
        return False
    except Exception as e:
        print(f"💥 未知错误: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 xAI API密钥测试工具")
    print("=" * 50)
    
    # 从命令行获取API密钥或要求用户输入
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = input("请输入您的xAI API密钥: ")
    
    # 验证密钥格式
    if re.match(r'^xai-[A-Za-z0-9]{50,}$', api_key):
        print("✅ API密钥格式正确")
    else:
        print("❌ API密钥格式不正确")
        print(f"📏 密钥长度: {len(api_key)}")
        print(f"🔍 密钥格式: {api_key[:5]}...")
        print("正确格式应为: xai-后跟50个以上字母数字字符")
        sys.exit(1)
    
    print()
    
    # 测试API密钥
    result = test_api_key(api_key)
    
    print()
    print("=" * 50)
    if result:
        print("🎉 测试完成：API密钥有效！")
    else:
        print("😞 测试完成：API密钥无效或存在其他问题") 