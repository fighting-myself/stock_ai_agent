from langchain_openai import ChatOpenAI
from config.settings import settings

class ModelFactory:
    @staticmethod
    def get_model(model_name: str):
        model_name = model_name.strip().lower()

        # 阿里云通义千问
        if "qwen" in model_name:
            return ChatOpenAI(
                model=settings.DEFAULT_MODEL,
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                temperature=0.1,
                max_tokens=4096
            )

        # 字节豆包
        elif "doubao" in model_name:
            return ChatOpenAI(
                model="doubao-seed-2-0-pro-260215",
                api_key=settings.DOUBAO_API_KEY,
                base_url="https://ark.cn-beijing.volces.com/api/v3",
                temperature=0.1
            )

        # DeepSeek
        elif "deepseek" in model_name:
            return ChatOpenAI(
                model="deepseek-chat",
                api_key=settings.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com",
                temperature=0.1
            )

        # MiniMax
        elif "minimax" in model_name:
            return ChatOpenAI(
                model="minimax-chat",
                api_key=settings.MINIMAX_API_KEY,
                base_url="https://api.minimax.chat/v1",
                temperature=0.1
            )

        # OpenAI GPT
        elif "gpt" in model_name:
            return ChatOpenAI(
                model=model_name,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.1
            )

        # 默认 fallback
        return ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )