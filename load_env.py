#!/usr/bin/env python3
"""
加载环境变量
"""
import os
from pathlib import Path

def load_env():
    """从 .env 文件加载环境变量"""
    env_file = Path(__file__).parent / '.env'

    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"✅ 已加载环境变量: {key}")
    else:
        print(f"❌ 未找到 .env 文件: {env_file}")

if __name__ == "__main__":
    load_env()
    print(f"DASHSCOPE_API_KEY: {os.environ.get('DASHSCOPE_API_KEY', 'Not found')[:20]}...")