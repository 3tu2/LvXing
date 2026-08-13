"""LLM服务模块。

LLM = Large Language Model,也就是"大语言模型"(如 GPT、DeepSeek 等)。
整个项目的"智能"都来自它:Agent 需要调用 LLM 来理解需求、决定调哪个工具、生成文字结果。

这个文件负责 LLM 的初始化与复用,采用"单例模式":只创建一个实例,到处共享。

用的是 LangChain 的 ChatOpenAI:DeepSeek 等国产模型大多兼容 OpenAI 接口,
只要把 base_url 指到对应服务地址,就能直接复用 ChatOpenAI 这个标准封装。
"""

import os
from langchain_openai import ChatOpenAI   # LangChain 的 OpenAI 兼容 LLM 封装

# 全局LLM实例(先设为 None,首次使用时才创建)
_llm_instance = None


def get_llm() -> ChatOpenAI:
    """
    获取LLM实例(单例模式)。

    从环境变量读取配置(和 .env 文件里的变量一一对应):
    - LLM_MODEL_ID  模型名称(如 deepseek-chat、gpt-4o)
    - LLM_API_KEY   API 密钥
    - LLM_BASE_URL  服务地址(DeepSeek 是 https://api.deepseek.com)
    - LLM_TIMEOUT   超时秒数(可选,默认 60)

    Returns:
        ChatOpenAI实例
    """
    global _llm_instance

    if _llm_instance is None:
        # ChatOpenAI 需要显式传入这些参数(不再像旧框架那样自动从环境变量读)
        _llm_instance = ChatOpenAI(
            model=os.getenv("LLM_MODEL_ID", "gpt-4o"),
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            timeout=float(os.getenv("LLM_TIMEOUT", "60")),
        )

        print(f"✅ LLM服务初始化成功")
        print(f"   模型: {_llm_instance.model_name}")
        print(f"   服务地址: {_llm_instance.openai_api_base}")

    return _llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)。

    把实例清空后,下一次调用 get_llm() 会重新初始化。
    """
    global _llm_instance
    _llm_instance = None
