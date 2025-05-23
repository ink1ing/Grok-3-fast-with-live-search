#!/usr/bin/env python3
"""
Grok 3.0 Chat Markdown 功能测试脚本
测试各种 Markdown 语法的渲染效果
"""

import requests
import json
import time

# 测试用的 Markdown 内容
test_messages = [
    {
        "name": "标题测试",
        "content": """# 一级标题
## 二级标题
### 三级标题
#### 四级标题"""
    },
    {
        "name": "代码块测试",
        "content": """这是一个 Python 代码示例：

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 计算前10个斐波那契数
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
```

这是一个 JavaScript 代码示例：

```javascript
const greet = (name) => {
    return `Hello, ${name}! 欢迎使用 Grok 3.0`;
};

console.log(greet("用户"));
```"""
    },
    {
        "name": "数学公式测试",
        "content": """数学公式渲染测试：

行内公式：爱因斯坦质能方程 $E = mc^2$

块级公式：
$$\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}$$

二次方程求根公式：
$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$"""
    },
    {
        "name": "表格测试",
        "content": """功能对比表格：

| 功能 | 状态 | 说明 | 优先级 |
|------|------|------|--------|
| Markdown 渲染 | ✅ 完成 | 支持完整语法 | 高 |
| 代码高亮 | ✅ 完成 | 多语言支持 | 高 |
| 数学公式 | ✅ 完成 | LaTeX 语法 | 中 |
| 响应式设计 | ✅ 完成 | 多端适配 | 高 |
| Live Search | ✅ 完成 | 实时搜索 | 中 |"""
    },
    {
        "name": "列表和引用测试",
        "content": """列表示例：

**有序列表：**
1. 第一项
2. 第二项
   1. 子项目 A
   2. 子项目 B
3. 第三项

**无序列表：**
- 项目一
- 项目二
  - 子项目 α
  - 子项目 β
- 项目三

**引用块：**
> 这是一个引用块的示例
> 
> 可以包含多行内容
> 
> > 这是嵌套引用"""
    },
    {
        "name": "链接和强调测试",
        "content": """文本格式化测试：

**粗体文本** 和 *斜体文本* 以及 ***粗斜体文本***

~~删除线文本~~

`行内代码` 示例

[链接到 xAI 官网](https://x.ai)

---

分割线上方的内容

---

分割线下方的内容"""
    }
]

def test_markdown_rendering():
    """测试 Markdown 渲染功能"""
    print("🧪 开始测试 Grok 3.0 Chat Markdown 渲染功能")
    print("=" * 60)
    
    # 检查应用是否运行
    try:
        response = requests.get("http://localhost:10000/health", timeout=5)
        if response.status_code == 200:
            print("✅ 应用运行正常")
        else:
            print("❌ 应用状态异常")
            return
    except requests.exceptions.RequestException:
        print("❌ 无法连接到应用，请确保应用正在运行")
        return
    
    print("\n📝 Markdown 测试用例：")
    print("-" * 40)
    
    for i, test_case in enumerate(test_messages, 1):
        print(f"\n{i}. {test_case['name']}")
        print("内容预览：")
        preview = test_case['content'][:100].replace('\n', ' ')
        print(f"   {preview}...")
        
        # 显示完整内容
        print("\n完整内容：")
        print("```")
        print(test_case['content'])
        print("```")
        
        input("\n按 Enter 继续下一个测试用例...")
    
    print("\n🎯 测试建议：")
    print("1. 在浏览器中打开 http://localhost:10000")
    print("2. 设置您的 xAI API 密钥")
    print("3. 复制上述测试内容发送给 Grok 3.0")
    print("4. 观察 Markdown 渲染效果")
    
    print("\n✨ 预期效果：")
    print("- 标题应该有不同的字体大小")
    print("- 代码块应该有语法高亮")
    print("- 数学公式应该正确渲染")
    print("- 表格应该有边框和对齐")
    print("- 列表应该有正确的缩进")
    print("- 引用块应该有特殊样式")
    print("- 链接应该可以点击")

def test_responsive_design():
    """测试响应式设计"""
    print("\n📱 响应式设计测试指南：")
    print("-" * 40)
    
    breakpoints = [
        ("移动端", "< 768px", "侧边栏应该隐藏，显示切换按钮"),
        ("平板", "768px - 1024px", "侧边栏宽度调整，消息宽度适配"),
        ("桌面", "> 1024px", "完整布局，最佳体验"),
        ("大屏", "> 1400px", "更宽的侧边栏，更好的空间利用")
    ]
    
    for device, size, description in breakpoints:
        print(f"📐 {device} ({size}): {description}")
    
    print("\n🔧 测试方法：")
    print("1. 打开浏览器开发者工具 (F12)")
    print("2. 切换到设备模拟模式")
    print("3. 测试不同屏幕尺寸")
    print("4. 检查布局是否正确适配")

if __name__ == "__main__":
    test_markdown_rendering()
    test_responsive_design()
    
    print("\n🎉 测试完成！")
    print("如有问题，请检查：")
    print("- 浏览器控制台错误信息")
    print("- 网络请求状态")
    print("- API 密钥配置")
    print("- JavaScript 是否启用") 