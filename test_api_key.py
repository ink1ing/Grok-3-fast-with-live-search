#!/usr/bin/env python3
"""
测试xAI API密钥的有效性
"""
import requests
import json

def test_api_key(api_key):
    """测试API密钥是否有效"""
    
    print(f"🔑 测试API密钥: {api_key[:10]}...{api_key[-10:]}")
    
    # 构建请求
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    data = {
        "model": "grok-4-latest",
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
    # 您的API密钥（请在此处输入您的实际API密钥）
    api_key = "YOUR_API_KEY_HERE"
    
    print("🚀 xAI API密钥测试工具")
    print("=" * 50)
    
    # 验证密钥格式
    import re
    if re.match(r'^xai-[A-Za-z0-9]{50,}$', api_key):
        print("✅ API密钥格式正确")
    else:
        print("❌ API密钥格式不正确")
        print(f"📏 密钥长度: {len(api_key)}")
        print(f"🔍 密钥格式: {api_key[:20]}...")
    
    print()
    
    # 测试API密钥
    result = test_api_key(api_key)
    
    print()
    print("=" * 50)
    if result:
        print("🎉 测试完成：API密钥有效！")
    else:
        print("😞 测试完成：API密钥无效或存在其他问题") 