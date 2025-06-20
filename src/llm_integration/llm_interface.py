import os
from enum import Enum
from typing import Any, Dict, List, Optional

import openai
from langchain.chat_models import ChatOpenAI
from langchain.llms import HuggingFacePipeline, LlamaCpp
from langchain.schema import HumanMessage, SystemMessage
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from ..utils.config import Config


class LLMProvider(Enum):
    OPENAI = "openai"
    LLAMA = "llama"
    MISTRAL = "mistral"
    LOCAL = "local"


class LLMInterface:
    """Unified interface for different LLM providers."""

    def __init__(self, config: Config):
        self.config = config
        self.provider = LLMProvider(config.llm.provider)
        self.model = self._initialize_model()

    def _initialize_model(self):
        """Initialize the appropriate LLM based on configuration."""
        if self.provider == LLMProvider.OPENAI:
            return self._init_openai()
        elif self.provider == LLMProvider.LLAMA:
            return self._init_llama()
        elif self.provider == LLMProvider.MISTRAL:
            return self._init_mistral()
        elif self.provider == LLMProvider.LOCAL:
            return self._init_local_model()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _init_openai(self):
        """Initialize OpenAI model."""
        api_key = self.config.llm.api_key or os.getenv("OPENAI_API_KEY")

        return ChatOpenAI(
            model_name=self.config.llm.model_name,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            openai_api_key=api_key,
        )

    def _init_llama(self):
        """Initialize Llama model."""
        model_path = self.config.llm.model_path

        return LlamaCpp(
            model_path=model_path,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            n_ctx=self.config.llm.context_length,
            n_gpu_layers=self.config.llm.gpu_layers,
        )

    def _init_mistral(self):
        """Initialize Mistral model."""
        model_name = self.config.llm.model_name or "mistralai/Mistral-7B-Instruct-v0.1"

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, device_map="auto", torch_dtype="auto"
        )

        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=self.config.llm.max_tokens,
            temperature=self.config.llm.temperature,
        )

        return HuggingFacePipeline(pipeline=pipe)

    def _init_local_model(self):
        """Initialize local model (e.g., via Ollama)"""
        # This would integrate with Ollama or similar local model servers
        # For now, we'll use a placeholder
        logger.info("Initializing local model connection...")
        # Implementation would depend on specific local model setup
        pass

    async def generate_response(self, prompt: Dict[str, str], streaming: bool = False) -> str:
        """Generate response from LLM."""
        try:
            if self.provider == LLMProvider.OPENAI:
                messages = [
                    SystemMessage(content=prompt["system"]),
                    HumanMessage(content=prompt["user"]),
                ]

                if streaming:
                    # This should be a separate method for streaming
                    response = await self.model.ainvoke(messages)
                    return response.content
                else:
                    response = await self.model.ainvoke(messages)
                    return response.content

            else:
                # For other providers, use synchronous generation
                full_prompt = f"{prompt['system']}\n\n{prompt['user']}"
                response = self.model(full_prompt)

                if isinstance(response, dict):
                    return response.get("text", "")
                return str(response)

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            raise

    async def generate_streaming_response(self, prompt: Dict[str, str]):
        """Generate streaming response from LLM."""
        try:
            if self.provider == LLMProvider.OPENAI:
                messages = [
                    SystemMessage(content=prompt["system"]),
                    HumanMessage(content=prompt["user"]),
                ]

                async for chunk in self.model.astream(messages):
                    yield chunk.content
            else:
                # For non-streaming providers, yield the full response at once
                response = await self.generate_response(prompt, streaming=False)
                yield response

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield f"Error: {str(e)}"

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.provider == LLMProvider.OPENAI:
            # Use tiktoken for OpenAI models
            import tiktoken

            enc = tiktoken.encoding_for_model(self.config.llm.model_name)
            return len(enc.encode(text))
        else:
            # Rough estimate for other models
            return len(text.split()) * 1.3
