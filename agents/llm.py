# -*- coding: utf-8 -*-
# @Time    : 2026/5/19 12:00
# @Author  : Zery
# @File    : llm.py
# @Software: PyCharm
# agents/llm.py

"""
LLM 统一客户端。

本文件只负责一件事：把“消息 + 模型配置”发送给模型，并返回统一格式的结果。
上层 Agent 不需要关心底层用 Responses API 还是 Chat Completions API。
"""

from typing import Any, Dict, List, Optional, Union

from openai import OpenAI
from agents.config import AppConfig
from utils.logger import logger

Message = Dict[str, str]
MessagesInput = Union[str, List[Message]]


class LLMClient:
    """
    OpenAI / 中转站 / 兼容 OpenAI 协议模型的统一客户端。

    支持两种模式：
    - responses：OpenAI Responses API
    - chat：Chat Completions API，适合部分中转站或 MiMo 这类兼容接口
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.from_env()
        if not self.config.api_key:
            raise RuntimeError("API Key 丢失，请在 .env 中配置 AGENT_API_KEY 或 OPENAI_API_KEY。")

        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def get_models(self) -> Optional[List[Any]]:
        """
        获取当前 API Key / base_url 可用的模型列表。
        """
        try:
            models = self.client.models.list()
            logger.info(f"可用的模型: {[model.id for model in models.data]}")
            return models.data
        except Exception as e:
            logger.error(f"获取模型时出错: {e}")
            return None

    def generate_response(
        self,
        messages: MessagesInput,
        model: Optional[str] = None,
        llm_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成响应，并统一返回字段。

        Args:
            messages: 字符串 prompt，或 OpenAI 消息列表。
            model: 本次调用使用的模型；为空时使用配置里的默认模型。
            llm_mode: responses / chat；为空时使用配置里的默认模式。
        """
        selected_model = model or self.config.default_model
        selected_mode = (llm_mode or self.config.llm_mode).lower()

        if selected_mode == "chat":
            return self._generate_with_chat(messages, selected_model)
        if selected_mode == "responses":
            return self._generate_with_responses(messages, selected_model)

        raise ValueError(f"不支持的 LLM 调用模式: {selected_mode}，请使用 responses 或 chat。")

    def _generate_with_responses(self, messages: MessagesInput, model: str) -> Dict[str, Any]:
        """
        使用 Responses API 调用模型。
        """
        try:
            response = self.client.responses.create(
                model=model,
                input=messages,
                stream=False,
            )
            return {
                "id": response.id,
                "model": response.model,
                "status": response.status,
                "content": response.output_text,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
        except Exception as e:
            logger.error(f"Responses API 生成响应时出错: {e}")
            raise

    def _generate_with_chat(self, messages: MessagesInput, model: str) -> Dict[str, Any]:
        """
        使用 Chat Completions API 调用模型。

        一些兼容 OpenAI 协议的服务只支持 chat.completions，
        例如你当前尝试的 MiMo 风格接口，就可以通过 AGENT_LLM_MODE=chat 切换。
        """
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=self._to_chat_messages(messages),
                max_completion_tokens=self.config.max_completion_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                stream=False,
            )
            message = completion.choices[0].message
            usage = completion.usage
            return {
                "id": completion.id,
                "model": completion.model,
                "status": "completed",
                "content": message.content or "",
                "usage": {
                    "input_tokens": getattr(usage, "prompt_tokens", None),
                    "output_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                },
            }
        except Exception as e:
            logger.error(f"Chat Completions API 生成响应时出错: {e}")
            raise

    @staticmethod
    def _to_chat_messages(messages: MessagesInput) -> List[Message]:
        """
        将字符串 prompt 转成 chat.completions 可接受的消息列表。
        """
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        return messages


if __name__ == "__main__":
    # 简单调试入口：只获取模型列表，不主动发起对话请求。
    llm_client = LLMClient()
    llm_client.get_models()
