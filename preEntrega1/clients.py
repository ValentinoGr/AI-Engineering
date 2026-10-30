from abc import ABC, abstractmethod
from typing import AsyncGenerator, List

from anthropic import (
    AsyncAnthropic,
    APIError as AnthropicAPIError,
    RateLimitError as AnthropicRateLimitError,
    APIConnectionError as AnthropicConnectionError,
)
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from schemas import ChatMessage, ModelResponse, Provider


class BaseLLMClient(ABC):
    """Contrato que todo cliente de LLM debe cumplir, sin importar el proveedor real detrás."""

    @abstractmethod
    async def generate(self, messages: List[ChatMessage]) -> ModelResponse:
        """Genera una respuesta completa (modo normal, no streaming)."""
        raise NotImplementedError

    @abstractmethod
    async def generate_stream(
        self, messages: List[ChatMessage]
    ) -> AsyncGenerator[str, None]:
        """Genera la respuesta token a token (modo streaming)."""
        raise NotImplementedError
        yield  # nunca se ejecuta; solo le indica a Python que este método es un generador


class OpenAIClient(BaseLLMClient):
    provider = Provider.OPENAI

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        base_url: str | None = None,
    ):
        self._client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=30.0, max_retries=1
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate(self, messages: List[ChatMessage]) -> ModelResponse:
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[m.model_dump() for m in messages],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return ModelResponse(
                provider=self.provider,
                model=self.model,
                content=response.choices[0].message.content,
            )
        except RateLimitError as e:
            return ModelResponse(
                provider=self.provider,
                model=self.model,
                content="",
                error=f"Límite de cuota excedido: {e}",
            )
        except APIConnectionError as e:
            return ModelResponse(
                provider=self.provider,
                model=self.model,
                content="",
                error=f"Error de conexión: {e}",
            )
        except APIError as e:
            return ModelResponse(
                provider=self.provider,
                model=self.model,
                content="",
                error=f"Error de la API de OpenAI: {e}",
            )

    async def generate_stream(
        self, messages: List[ChatMessage]
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=[m.model_dump() for m in messages],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except (RateLimitError, APIConnectionError, APIError) as e:
            yield f"\n[⚠️ Error durante el streaming: {e}]"


class GeminiClient(OpenAIClient):
    """Gemini a través de su endpoint compatible con el SDK de OpenAI."""

    provider = Provider.GEMINI
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        super().__init__(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=self.BASE_URL,
        )


class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self._client = AsyncAnthropic(api_key=api_key, timeout=30.0, max_retries=1)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @staticmethod
    def _preparar(messages: List[ChatMessage]) -> dict:
        """Anthropic no acepta el rol 'system' dentro de messages: va en un parámetro aparte."""
        system = "\n".join(m.content for m in messages if m.role == "system")
        kwargs = {
            "messages": [m.model_dump() for m in messages if m.role != "system"]
        }
        if system:
            kwargs["system"] = system
        return kwargs

    async def generate(self, messages: List[ChatMessage]) -> ModelResponse:
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,  # obligatorio en Anthropic, a diferencia de OpenAI
                temperature=self.temperature,
                **self._preparar(messages),
            )
            return ModelResponse(
                provider=Provider.ANTHROPIC,
                model=self.model,
                content=response.content[0].text,
            )
        except AnthropicRateLimitError as e:
            return ModelResponse(
                provider=Provider.ANTHROPIC,
                model=self.model,
                content="",
                error=f"Límite de cuota excedido: {e}",
            )
        except AnthropicConnectionError as e:
            return ModelResponse(
                provider=Provider.ANTHROPIC,
                model=self.model,
                content="",
                error=f"Error de conexión: {e}",
            )
        except AnthropicAPIError as e:
            return ModelResponse(
                provider=Provider.ANTHROPIC,
                model=self.model,
                content="",
                error=f"Error de la API de Anthropic: {e}",
            )

    async def generate_stream(
        self, messages: List[ChatMessage]
    ) -> AsyncGenerator[str, None]:
        try:
            async with self._client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                **self._preparar(messages),
            ) as stream:
                async for texto in stream.text_stream:
                    yield texto
        except (
            AnthropicRateLimitError,
            AnthropicConnectionError,
            AnthropicAPIError,
        ) as e:
            yield f"\n[⚠️ Error durante el streaming: {e}]"
