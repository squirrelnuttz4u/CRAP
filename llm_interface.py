# llm_interface.py
# © 2025 Colt McVey
# The Concurrent Inference Engine for managing local and remote LLMs.

import asyncio
import aiohttp
import json
import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator

from settings_manager import settings_manager

API_KEYS = {
    "openai": os.environ.get("OPENAI_API_KEY"),
}

class BaseLLMProvider(ABC):
    @abstractmethod
    async def list_models(self) -> List[str]:
        pass

    @abstractmethod
    async def generate_stream(self, model: str, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        yield ""

class OllamaProvider(BaseLLMProvider):
    """Provider for a local Ollama instance. Reads configuration from settings."""
    def __init__(self):
        host = settings_manager.get("ollama_host")
        port = settings_manager.get("ollama_port")
        self.base_url = f"{host}:{port}"

    async def list_models(self) -> List[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    response.raise_for_status()
                    data = await response.json()
                    return [model['name'] for model in data.get('models', [])]
        except aiohttp.ClientError:
            logging.warning(f"Could not connect to Ollama server at {self.base_url}. Is it running?")
            return []

    async def generate_stream(self, model: str, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        """
        Sends a structured list of messages to the Ollama /api/chat endpoint.
        """
        payload = {
            "model": model,
            "messages": messages, # Use the conversational messages format
            "stream": True
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                # The response for /api/chat is nested differently
                                yield data.get("message", {}).get("content", "")
                                if data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                logging.warning(f"Ollama stream sent invalid JSON line: {line}")
                                continue
        except aiohttp.ClientError as e:
            logging.error(f"Ollama request failed: {e}")
            yield f"\n[Ollama Error: {e}]"

    async def embed(self, model: str, text: str) -> List[float]:
        """Generates a vector embedding for a given text."""
        payload = {"model": model, "prompt": text}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/embeddings", json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("embedding", [])
        except aiohttp.ClientError as e:
            logging.error(f"Ollama embedding request failed: {e}")
            return []

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"

    async def list_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

    async def generate_stream(self, model: str, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "stream": True}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.content:
                        if line.strip().startswith(b'data: '):
                            line = line[len(b'data: '):]
                        if line.strip() == b'[DONE]': break
                        if line.strip():
                            try:
                                delta = json.loads(line).get("choices", [{}])[0].get("delta", {})
                                if "content" in delta: yield delta["content"]
                            except json.JSONDecodeError: continue
        except aiohttp.ClientError as e:
            yield f"\n[OpenAI Error: {e}]"

class InferenceEngine:
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._register_providers()

    def _register_providers(self):
        self.providers['ollama'] = OllamaProvider()
        if API_KEYS["openai"]:
            self.providers['openai'] = OpenAIProvider(api_key=API_KEYS["openai"])
        else:
            logging.info("OpenAI provider not registered: API key not found in environment variables.")

    async def get_all_models(self) -> Dict[str, List[str]]:
        tasks = [p.list_models() for p in self.providers.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {name: res for name, res in zip(self.providers.keys(), results) if isinstance(res, list)}

    async def battle(self, models: List[str], messages: List[Dict]) -> List[AsyncGenerator[str, None]]:
        tasks = []
        for model_id in models:
            provider_name, model_name = model_id.split('/', 1)
            if provider := self.providers.get(provider_name):
                tasks.append(provider.generate_stream(model_name, messages))
            else:
                async def error_gen(): yield f"[Error: Provider '{provider_name}' not found]"
                tasks.append(error_gen())
        return tasks

    async def embed(self, model_id: str, text: str) -> List[float]:
        """Routes an embedding request to the correct provider."""
        provider_name, model_name = model_id.split('/', 1) if '/' in model_id else ("ollama", model_id)
        
        if provider := self.providers.get(provider_name):
            if hasattr(provider, 'embed'):
                return await provider.embed(model_name, text)
        
        logging.warning(f"Embedding provider '{provider_name}' not found or does not support embeddings.")
        return []