#!/usr/bin/env python3
"""
阿里云 Qwen 图片生成 MCP 服务
实现 Model Context Protocol，为 AI 客户端提供图片生成能力
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Literal
from dataclasses import dataclass

try:
    import dashscope
    from dashscope import ImageSynthesis, MultiModalConversation
    from http import HTTPStatus
    import requests
except ImportError as e:
    print(f"❌ 缺少依赖库: {e}")
    print("请安装: pip install dashscope requests")
    sys.exit(1)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 类型定义
ImageSize = Literal[
    "1328*1328",    # 1:1 正方形
    "1664*928",     # 16:9 横屏
    "1472*1140",    # 4:3 标准
    "1140*1472",    # 3:4 竖屏
    "928*1664"      # 9:16 竖屏
]

ContentStyle = Literal[
    "general", "lifestyle", "food", "fashion", "travel",
    "beauty", "tech", "art", "traditional", "business",
    "nature", "portrait", "abstract", "cartoon"
]

Platform = Literal[
    "general", "xiaohongshu", "weibo", "douyin", "kuaishou",
    "instagram", "twitter", "facebook", "pinterest", "tiktok"
]

CallMode = Literal["sync", "async", "multimodal"]

@dataclass
class ImageGenerationResult:
    """图片生成结果"""
    success: bool
    image_url: Optional[str] = None
    local_path: Optional[str] = None
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    config_used: Optional[Dict[str, Any]] = None

class QwenImageMCPService:
    """阿里云 Qwen 图片生成 MCP 服务"""

    def __init__(self):
        self.protocol_version = "2025-03-26"
        self.server_info = {
            "name": "qwen-image-mcp",
            "version": "1.0.0"
        }
        self._style_templates = self._load_style_templates()
        self._platform_configs = self._load_platform_configs()

    def _load_style_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载风格模板"""
        return {
            "general": {
                "name": "通用",
                "base_prompt": "高质量图片",
                "negative_prompt": "低分辨率，错误，最差质量，低质量",
                "photography_style": "专业摄影",
                "lighting": "自然光线",
                "quality_keywords": ["高清", "精细", "清晰", "专业"]
            },
            "lifestyle": {
                "name": "生活方式",
                "base_prompt": "温馨生活场景，ins风格",
                "negative_prompt": "杂乱，阴暗，低质量",
                "photography_style": "生活摄影，自然抓拍",
                "lighting": "温暖自然光线",
                "quality_keywords": ["温馨", "自然", "生活感", "舒适"]
            },
            "food": {
                "name": "美食",
                "base_prompt": "美食摄影，精致摆盘",
                "negative_prompt": "模糊，暗淡，不新鲜，杂乱",
                "photography_style": "美食特写，精致摆盘",
                "lighting": "柔和自然光，突出食物色泽",
                "quality_keywords": ["诱人", "新鲜", "精致", "色彩鲜艳"]
            },
            "fashion": {
                "name": "时尚",
                "base_prompt": "时尚摄影，现代穿搭",
                "negative_prompt": "过时，廉价，杂乱，低质量",
                "photography_style": "时尚摄影，现代构图",
                "lighting": "专业打光，突出服装质感",
                "quality_keywords": ["时尚", "现代", "优雅", "高端"]
            },
            "travel": {
                "name": "旅行",
                "base_prompt": "旅行摄影，风景如画",
                "negative_prompt": "污染，破败，阴暗，模糊",
                "photography_style": "风景摄影，壮美构图",
                "lighting": "自然光线，展现景色美感",
                "quality_keywords": ["壮美", "自然", "清新", "辽阔"]
            },
            "beauty": {
                "name": "美妆",
                "base_prompt": "美妆护肤，清新自然",
                "negative_prompt": "粗糙，瑕疵，不自然，过度修饰",
                "photography_style": "美妆摄影，清新自然",
                "lighting": "柔和光线，突出肌肤质感",
                "quality_keywords": ["清新", "自然", "细腻", "光滑"]
            },
            "tech": {
                "name": "科技",
                "base_prompt": "科技产品，现代简约",
                "negative_prompt": "过时，复杂，杂乱，低端",
                "photography_style": "产品摄影，简约现代",
                "lighting": "专业打光，突出科技感",
                "quality_keywords": ["现代", "简约", "高科技", "精工"]
            },
            "art": {
                "name": "艺术",
                "base_prompt": "艺术创作，创意构图",
                "negative_prompt": "平庸，无创意，粗糙，低质量",
                "photography_style": "艺术摄影，创意表达",
                "lighting": "艺术光影，营造氛围",
                "quality_keywords": ["艺术", "创意", "独特", "富有表现力"]
            },
            "traditional": {
                "name": "传统文化",
                "base_prompt": "中国传统文化，古典雅致",
                "negative_prompt": "现代化，西式，粗糙，不协调",
                "photography_style": "传统文化摄影，古典构图",
                "lighting": "古典光影，传统韵味",
                "quality_keywords": ["古典", "雅致", "传统", "文化底蕴"]
            },
            "business": {
                "name": "商务",
                "base_prompt": "商务场景，专业正式",
                "negative_prompt": "随意，不专业，杂乱，低端",
                "photography_style": "商务摄影，正式构图",
                "lighting": "专业商务光线",
                "quality_keywords": ["专业", "正式", "高端", "商务"]
            },
            "nature": {
                "name": "自然",
                "base_prompt": "自然景观，生态环境",
                "negative_prompt": "人工，破坏，污染，不自然",
                "photography_style": "自然摄影，生态记录",
                "lighting": "自然光线，真实环境",
                "quality_keywords": ["自然", "生态", "真实", "和谐"]
            },
            "portrait": {
                "name": "人像",
                "base_prompt": "人物肖像，情感表达",
                "negative_prompt": "模糊，失真，不自然表情",
                "photography_style": "人像摄影，情感捕捉",
                "lighting": "人像打光，突出神态",
                "quality_keywords": ["生动", "自然", "有神", "情感丰富"]
            },
            "abstract": {
                "name": "抽象",
                "base_prompt": "抽象艺术，概念表达",
                "negative_prompt": "具象，写实，平庸，无创意",
                "photography_style": "抽象表现，概念艺术",
                "lighting": "创意光效，抽象表现",
                "quality_keywords": ["抽象", "概念", "创新", "独特"]
            },
            "cartoon": {
                "name": "卡通",
                "base_prompt": "卡通动漫，可爱风格",
                "negative_prompt": "写实，阴暗，成人内容",
                "photography_style": "卡通风格，动漫表现",
                "lighting": "明亮活泼，卡通光效",
                "quality_keywords": ["可爱", "活泼", "色彩鲜艳", "有趣"]
            }
        }

    def _load_platform_configs(self) -> Dict[str, Dict[str, Any]]:
        """加载平台配置"""
        return {
            "general": {
                "name": "通用",
                "suffix": "",
                "preferred_sizes": ["1328*1328", "1664*928", "1472*1140"],
                "style_modifier": ""
            },
            "xiaohongshu": {
                "name": "小红书",
                "suffix": "适合小红书分享，社交媒体风格",
                "preferred_sizes": ["1472*1140", "1328*1328", "1140*1472"],
                "style_modifier": "生活化，亲和力强"
            },
            "weibo": {
                "name": "微博",
                "suffix": "适合微博分享，话题性强",
                "preferred_sizes": ["1664*928", "1328*1328"],
                "style_modifier": "话题性，吸引眼球"
            },
            "douyin": {
                "name": "抖音",
                "suffix": "适合抖音短视频，竖屏优化",
                "preferred_sizes": ["928*1664", "1140*1472"],
                "style_modifier": "动感，年轻化"
            },
            "kuaishou": {
                "name": "快手",
                "suffix": "适合快手平台，接地气风格",
                "preferred_sizes": ["928*1664", "1328*1328"],
                "style_modifier": "真实，接地气"
            },
            "instagram": {
                "name": "Instagram",
                "suffix": "Instagram style, international aesthetic",
                "preferred_sizes": ["1328*1328", "1140*1472"],
                "style_modifier": "国际化，现代感"
            },
            "pinterest": {
                "name": "Pinterest",
                "suffix": "Pinterest optimized, visual impact",
                "preferred_sizes": ["1140*1472", "928*1664"],
                "style_modifier": "视觉冲击，创意"
            },
            "tiktok": {
                "name": "TikTok",
                "suffix": "TikTok ready, vertical format",
                "preferred_sizes": ["928*1664", "1140*1472"],
                "style_modifier": "年轻潮流，国际化"
            }
        }

    def _get_api_key(self, provided_key: Optional[str] = None) -> str:
        """获取API密钥"""
        api_key = provided_key or os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("API密钥未提供。请通过参数或环境变量 DASHSCOPE_API_KEY 设置")
        return api_key

    def _enhance_prompt(
        self,
        prompt: str,
        style: ContentStyle,
        platform: Platform,
        enable_enhancement: bool,
        custom_enhancement: Optional[str] = None
    ) -> str:
        """增强提示词"""
        if not enable_enhancement:
            return prompt

        enhanced_parts = [prompt]

        if custom_enhancement:
            enhanced_parts.append(custom_enhancement)

        style_template = self._style_templates.get(style, self._style_templates["general"])

        if style_template["base_prompt"] and style_template["base_prompt"] not in prompt:
            enhanced_parts.append(style_template["base_prompt"])

        if style_template["photography_style"]:
            enhanced_parts.append(style_template["photography_style"])

        if style_template["lighting"]:
            enhanced_parts.append(style_template["lighting"])

        if style_template["quality_keywords"]:
            enhanced_parts.extend(style_template["quality_keywords"])

        platform_config = self._platform_configs.get(platform, self._platform_configs["general"])
        if platform_config["suffix"]:
            enhanced_parts.append(platform_config["suffix"])

        if platform_config["style_modifier"]:
            enhanced_parts.append(platform_config["style_modifier"])

        return "，".join(enhanced_parts)

    def _get_negative_prompt(self, style: ContentStyle, custom_negative: Optional[str] = None) -> str:
        """获取反向提示词"""
        negative_parts = []

        if custom_negative:
            negative_parts.append(custom_negative)

        style_template = self._style_templates.get(style, self._style_templates["general"])
        if style_template["negative_prompt"]:
            negative_parts.append(style_template["negative_prompt"])

        return "，".join(negative_parts)

    def _generate_filename(self, prompt: str, style: str, size: str) -> str:
        """生成文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        size_str = size.replace("*", "x")
        unique_id = str(uuid.uuid4())[:8]

        # 截取提示词的前10个字符作为描述
        desc = prompt[:10].replace(" ", "_").replace("，", "_").replace(",", "_")

        return f"qwen_{timestamp}_{size_str}_{style}_{desc}_{unique_id}.png"

    async def _download_image(self, url: str, filename: str, output_dir: str = "generated_images") -> str:
        """下载图片到本地"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"图片已下载到: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            raise

    async def _call_qwen_api(
        self,
        prompt: str,
        api_key: str,
        negative_prompt: str,
        size: ImageSize,
        model: str,
        call_mode: CallMode,
        prompt_extend: bool,
        watermark: bool,
        seed: Optional[int]
    ) -> Dict[str, Any]:
        """调用Qwen API"""
        os.environ["DASHSCOPE_API_KEY"] = api_key

        parameters = {
            "size": size,
            "prompt_extend": prompt_extend,
            "watermark": watermark
        }

        if negative_prompt:
            parameters["negative_prompt"] = negative_prompt

        if seed is not None:
            parameters["seed"] = seed

        try:
            if call_mode == "multimodal":
                messages = [{"role": "user", "content": [{"text": prompt}]}]

                response = MultiModalConversation.call(
                    api_key=api_key,
                    model=model,
                    messages=messages,
                    result_format='message',
                    stream=False,
                    **parameters
                )

                if response.status_code == 200:
                    return response
                else:
                    raise Exception(f"多模态API调用失败: {response.code} - {response.message}")

            else:
                parameters["n"] = 1

                if call_mode == "async":
                    response = ImageSynthesis.async_call(
                        api_key=api_key,
                        model=model,
                        prompt=prompt,
                        **parameters
                    )

                    task_id = response.output.task_id
                    while True:
                        result = ImageSynthesis.fetch(task_id, api_key=api_key)
                        if result.output.task_status == "SUCCEEDED":
                            return result
                        elif result.output.task_status == "FAILED":
                            raise Exception(f"异步任务失败: {result.output}")
                        await asyncio.sleep(3)
                else:
                    response = ImageSynthesis.call(
                        api_key=api_key,
                        model=model,
                        prompt=prompt,
                        **parameters
                    )

                    if response.status_code == HTTPStatus.OK:
                        return response
                    else:
                        raise Exception(f"同步API调用失败: {response.code} - {response.message}")

        except Exception as e:
            logger.error(f"API调用失败: {e}")
            raise

    async def generate_image(
        self,
        prompt: str,
        api_key: Optional[str] = None,
        style: ContentStyle = "general",
        platform: Platform = "general",
        size: ImageSize = "1328*1328",
        model: str = "qwen-image",
        call_mode: CallMode = "multimodal",
        prompt_extend: bool = True,
        watermark: bool = False,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        enable_enhancement: bool = True,
        custom_enhancement: Optional[str] = None,
        save_local: bool = True,
        output_dir: str = "generated_images"
    ) -> ImageGenerationResult:
        """生成图片"""
        start_time = datetime.now()

        try:
            actual_api_key = self._get_api_key(api_key)

            logger.info(f"生成图片 - 提示词: {prompt}, 风格: {style}, 尺寸: {size}")

            # 增强提示词
            enhanced_prompt = self._enhance_prompt(
                prompt=prompt,
                style=style,
                platform=platform,
                enable_enhancement=enable_enhancement,
                custom_enhancement=custom_enhancement
            )

            # 获取反向提示词
            final_negative_prompt = self._get_negative_prompt(style, negative_prompt)

            # 调用API
            response = await self._call_qwen_api(
                prompt=enhanced_prompt,
                api_key=actual_api_key,
                negative_prompt=final_negative_prompt,
                size=size,
                model=model,
                call_mode=call_mode,
                prompt_extend=prompt_extend,
                watermark=watermark,
                seed=seed
            )

            # 提取图片URL
            if call_mode == "multimodal":
                image_url = response.output.choices[0].message.content[0]['image']
            else:
                image_url = response.output.results[0].url

            # 处理本地保存
            local_path = None
            if save_local:
                filename = self._generate_filename(prompt, style, size)
                local_path = await self._download_image(image_url, filename, output_dir)

            generation_time = (datetime.now() - start_time).total_seconds()

            config_used = {
                "prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "style": style,
                "platform": platform,
                "size": size,
                "model": model,
                "call_mode": call_mode,
                "prompt_extend": prompt_extend,
                "watermark": watermark,
                "negative_prompt": final_negative_prompt,
                "seed": seed
            }

            return ImageGenerationResult(
                success=True,
                image_url=image_url,
                local_path=local_path,
                generation_time=generation_time,
                config_used=config_used
            )

        except Exception as e:
            generation_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"生成图片失败: {str(e)}"
            logger.error(error_msg)

            return ImageGenerationResult(
                success=False,
                error_message=error_msg,
                generation_time=generation_time
            )

    # MCP 协议方法
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化请求"""
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": {
                "tools": {}
            },
            "serverInfo": self.server_info
        }

    async def handle_tools_list(self) -> Dict[str, Any]:
        """处理工具列表请求"""
        tools = [
            {
                "name": "generate_image",
                "description": "使用阿里云 Qwen 生成高质量图片",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "图片描述提示词（必填）"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "阿里云 DashScope API 密钥（可选，可通过环境变量设置）"
                        },
                        "style": {
                            "type": "string",
                            "enum": list(self._style_templates.keys()),
                            "description": "图片风格（默认: general）",
                            "default": "general"
                        },
                        "platform": {
                            "type": "string",
                            "enum": list(self._platform_configs.keys()),
                            "description": "目标平台（默认: general）",
                            "default": "general"
                        },
                        "size": {
                            "type": "string",
                            "enum": ["1328*1328", "1664*928", "1472*1140", "1140*1472", "928*1664"],
                            "description": "图片尺寸（默认: 1328*1328）",
                            "default": "1328*1328"
                        },
                        "model": {
                            "type": "string",
                            "description": "模型名称（默认: qwen-image）",
                            "default": "qwen-image"
                        },
                        "call_mode": {
                            "type": "string",
                            "enum": ["sync", "async", "multimodal"],
                            "description": "调用模式（默认: multimodal）",
                            "default": "multimodal"
                        },
                        "prompt_extend": {
                            "type": "boolean",
                            "description": "是否启用智能改写（默认: true）",
                            "default": True
                        },
                        "watermark": {
                            "type": "boolean",
                            "description": "是否添加水印（默认: false）",
                            "default": False
                        },
                        "negative_prompt": {
                            "type": "string",
                            "description": "反向提示词（可选）"
                        },
                        "seed": {
                            "type": "integer",
                            "description": "随机种子（可选）"
                        },
                        "enable_enhancement": {
                            "type": "boolean",
                            "description": "是否启用提示词增强（默认: true）",
                            "default": True
                        },
                        "custom_enhancement": {
                            "type": "string",
                            "description": "自定义增强文本（可选）"
                        },
                        "save_local": {
                            "type": "boolean",
                            "description": "是否保存到本地（默认: true）",
                            "default": True
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "输出目录（默认: generated_images）",
                            "default": "generated_images"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "list_styles",
                "description": "获取所有可用的图片风格",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_platforms",
                "description": "获取所有支持的目标平台",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_style_info",
                "description": "获取特定风格的详细信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "style": {
                            "type": "string",
                            "enum": list(self._style_templates.keys()),
                            "description": "风格名称"
                        }
                    },
                    "required": ["style"]
                }
            }
        ]

        return {"tools": tools}

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用"""
        try:
            if name == "generate_image":
                result = await self.generate_image(**arguments)

                response_data = {
                    "success": result.success,
                    "image_url": result.image_url,
                    "local_path": result.local_path,
                    "generation_time": result.generation_time
                }

                if result.error_message:
                    response_data["error_message"] = result.error_message

                if result.config_used:
                    response_data["config_used"] = result.config_used

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(response_data, ensure_ascii=False, indent=2)
                        }
                    ]
                }

            elif name == "list_styles":
                styles = {k: v["name"] for k, v in self._style_templates.items()}
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(styles, ensure_ascii=False, indent=2)
                        }
                    ]
                }

            elif name == "list_platforms":
                platforms = {k: v["name"] for k, v in self._platform_configs.items()}
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(platforms, ensure_ascii=False, indent=2)
                        }
                    ]
                }

            elif name == "get_style_info":
                style = arguments.get("style")
                if style in self._style_templates:
                    style_info = self._style_templates[style]
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(style_info, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"未找到风格: {style}"
                            }
                        ],
                        "isError": True
                    }

            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"未知工具: {name}"
                        }
                    ],
                    "isError": True
                }

        except Exception as e:
            logger.error(f"工具调用失败: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"工具调用失败: {str(e)}"
                    }
                ],
                "isError": True
            }

    async def run_mcp_server(self):
        """运行 MCP 服务器"""
        import sys

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    continue

                response = await self.handle_mcp_request(request)
                print(json.dumps(response, ensure_ascii=False))
                sys.stdout.flush()

            except Exception as e:
                logger.error(f"处理请求失败: {e}")

    async def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 MCP 请求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_tools_list()
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, tool_args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"未知方法: {method}"
                    }
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"内部错误: {str(e)}"
                }
            }

if __name__ == "__main__":
    service = QwenImageMCPService()
    asyncio.run(service.run_mcp_server())