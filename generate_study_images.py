#!/usr/bin/env python3
"""
生成学习日常主题的图片
"""
import os
import asyncio
from qwen_image_mcp import QwenImageMCPService
from load_env import load_env

# 加载环境变量
load_env()

async def generate_study_images():
    """生成学习主题图片"""
    # 检查 API key
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 请设置 DASHSCOPE_API_KEY 环境变量")
        print("⏭️  跳过AI生成，使用现有图片")
        return []

    service = QwenImageMCPService()

    # 创建输出目录
    output_dir = "generated_images"
    os.makedirs(output_dir, exist_ok=True)

    # 定义图片生成任务 - 学习日常主题
    tasks = [
        {
            "name": "整洁学习桌面",
            "prompt": "整洁有序的学习桌面，MacBook笔记本电脑，咖啡杯，笔记本，暖色调灯光，现代简约风格",
            "style": "lifestyle",
            "platform": "xiaohongshu",
            "size": "1472*1140"
        },
        {
            "name": "编程代码界面",
            "prompt": "程序员编程界面，代码编辑器屏幕，Python代码，专业显示器，键盘鼠标，科技感",
            "style": "tech",
            "platform": "xiaohongshu",
            "size": "1472*1140"
        },
        {
            "name": "学习笔记本",
            "prompt": "精美的学习笔记本摊开，手写笔记，彩色标记笔，知识框架图，文艺清新风格",
            "style": "lifestyle",
            "platform": "xiaohongshu",
            "size": "1472*1140"
        }
    ]

    results = []
    for i, task in enumerate(tasks, 1):
        try:
            print(f"\n🎨 正在生成第{i}张图片: {task['name']}")
            print(f"   提示词: {task['prompt']}")

            result = await service.generate_image(
                prompt=task['prompt'],
                api_key=api_key,
                style=task['style'],
                platform=task['platform'],
                size=task['size'],
                output_dir=output_dir
            )

            if result.success:
                print(f"✅ 生成成功!")
                print(f"   文件路径: {result.local_path}")
                results.append({
                    "name": task['name'],
                    "path": result.local_path,
                    "success": True
                })
            else:
                print(f"❌ 生成失败: {result.error}")
                results.append({
                    "name": task['name'],
                    "error": result.error,
                    "success": False
                })

        except Exception as e:
            print(f"❌ 生成第{i}张图片时出错: {e}")
            results.append({
                "name": task['name'],
                "error": str(e),
                "success": False
            })

    # 输出结果汇总
    print("\n" + "="*50)
    print("📊 生成结果汇总:")
    for i, result in enumerate(results, 1):
        if result['success']:
            print(f"{i}. ✅ {result['name']}: {result['path']}")
        else:
            print(f"{i}. ❌ {result['name']}: {result['error']}")

    return results

if __name__ == "__main__":
    asyncio.run(generate_study_images())