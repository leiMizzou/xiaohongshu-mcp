#!/usr/bin/env python3
"""
阿里云 Qwen 图片生成 MCP 服务启动脚本
"""
import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qwen_image_mcp import QwenImageMCPService
import asyncio

if __name__ == "__main__":
    service = QwenImageMCPService()
    asyncio.run(service.run_mcp_server())