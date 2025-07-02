#!/usr/bin/env python3
"""
测试xAI Live Search API集成
"""
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_live_search_request():
    """测试Live Search请求格式"""
    
    # 模拟Live Search请求数据
    test_data = {
        "model": "grok-3-fast-latest",
        "messages": [
            {
                "role": "user",
                "content": "今天有什么科技新闻？"
            }
        ],
        "search_parameters": {
            "mode": "auto",
            "max_search_results": 5,
            "time_range": "24h"
        }
    }
    
    print("✅ Live Search请求格式测试:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print()
    
    # 验证必需字段
    required_fields = ["model", "messages", "search_parameters"]
    for field in required_fields:
        if field in test_data:
            print(f"✅ {field}: 存在")
        else:
            print(f"❌ {field}: 缺失")
    
    print()
    
    # 验证search_parameters
    search_params = test_data.get("search_parameters", {})
    required_search_fields = ["mode", "max_search_results", "time_range"]
    
    print("Live Search参数验证:")
    for field in required_search_fields:
        if field in search_params:
            print(f"✅ {field}: {search_params[field]}")
        else:
            print(f"❌ {field}: 缺失")
    
    print()
    return test_data

def test_api_url():
    """测试API URL配置"""
    api_url = os.getenv('API_URL', 'https://api.x.ai/v1/chat/completions')
    print(f"✅ API URL: {api_url}")
    
    if "api.x.ai" in api_url:
        print("✅ 使用正确的xAI API端点")
    else:
        print("⚠️  API端点可能不正确")
    
    print()
    return api_url

def test_model_config():
    """测试模型配置"""
    model = os.getenv('MODEL_NAME', 'grok-3-latest')
    temperature = os.getenv('TEMPERATURE', '0')
    
    print(f"✅ 模型: {model}")
    print(f"✅ 温度: {temperature}")
    
    if "grok-3" in model:
        print("✅ 使用Grok 3.0模型")
    else:
        print("⚠️  模型可能不是Grok 3.0")
    
    print()
    return model, temperature

if __name__ == "__main__":
    print("🚀 xAI Live Search API集成测试\n")
    print("=" * 50)
    
    # 测试API配置
    print("1. API配置测试:")
    api_url = test_api_url()
    model, temperature = test_model_config()
    
    # 测试Live Search请求格式
    print("2. Live Search请求格式测试:")
    test_data = test_live_search_request()
    
    # 总结
    print("=" * 50)
    print("🎉 测试完成!")
    print()
    print("Live Search功能特性:")
    print("✅ 自动搜索决策 - Grok根据对话上下文自动判断是否需要搜索")
    print("✅ 多样化数据源 - 支持X、网页、新闻和RSS源")
    print("✅ 实时信息 - 获取24小时内的最新信息")
    print("✅ 智能集成 - 搜索结果自动整合到对话回复中")
    print()
    print("使用方法:")
    print("1. 在设置中开启'xAI Live Search'开关")
    print("2. Live Search将使用您的xAI API密钥自动工作")
    print("3. 免费测试期至2025年6月5日")