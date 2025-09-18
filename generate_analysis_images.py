#!/usr/bin/env python3
"""
生成分析类内容的配图
"""
import os
import asyncio
from qwen_image_mcp import QwenImageMCPService
from load_env import load_env

# 加载环境变量
load_env()

async def generate_analysis_images():
    """生成分析主题图片"""
    # 检查 API key
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 请设置 DASHSCOPE_API_KEY 环境变量")
        return []

    service = QwenImageMCPService()

    # 创建输出目录
    output_dir = "generated_images"
    os.makedirs(output_dir, exist_ok=True)

    # 定义图片生成任务 - 科技分析主题
    tasks = [
        {
            "name": "科技发展趋势图表",
            "prompt": "科技发展趋势分析图表，上升箭头，数据可视化，蓝色科技风格，专业商务背景",
            "style": "business",
            "platform": "xiaohongshu",
            "size": "1472*1140"
        },
        {
            "name": "AI芯片技术",
            "prompt": "先进的AI芯片，半导体技术，电路板特写，高科技感，金属质感，蓝光效果",
            "style": "tech",
            "platform": "xiaohongshu",
            "size": "1472*1140"
        },
        {
            "name": "数据中心服务器",
            "prompt": "现代化数据中心，服务器机架，蓝色指示灯，科技走廊，未来感设计",
            "style": "tech",
            "platform": "xiaohongshu",
            "size": "1472*1140"
        },
        {
            "name": "全球网络连接",
            "prompt": "全球互联网络示意图，地球模型，连接线条，数字化概念，深蓝色背景",
            "style": "tech",
            "platform": "xiaohongshu",
            "size": "1472*1140"
        },
        {
            "name": "创新实验室",
            "prompt": "现代科技实验室，研究人员工作场景，高科技设备，创新氛围，明亮照明",
            "style": "business",
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
    asyncio.run(generate_analysis_images())