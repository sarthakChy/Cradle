import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union, Literal

from cradle.provider.base import EmbeddingProvider, LLMProvider
from cradle.provider.llm.openai import OpenAIProvider
from cradle.config import Config
from cradle.log import Logger
from cradle.utils.file_utils import assemble_project_path
from cradle.utils.json_utils import load_json


config = Config()
logger = Logger()

PROVIDER_SETTING_BASE_URL = "base_url"
PROVIDER_SETTING_COMP_MODEL = "comp_model"
PROVIDER_SETTING_EMB_MODEL = "emb_model"
PROVIDER_SETTING_TIMEOUT = "timeout"


class OllamaProvider(LLMProvider, EmbeddingProvider):
    """Ollama-backed provider for local chat completions and embeddings."""

    client: Any = None
    llm_model: str = ""
    embedding_model: str = ""

    allowed_special: Union[Literal["all"], Set[str]] = set()
    disallowed_special: Union[Literal["all"], Set[str], Sequence[str]] = "all"
    chunk_size: int = 1000
    embedding_ctx_length: int = 8191
    request_timeout: Optional[Union[float, Tuple[float, float]]] = None
    tiktoken_model_name: Optional[str] = None
    skip_empty: bool = False

    def __init__(self) -> None:
        self.retries = 5
        self.base_url = "http://localhost:11434"
        self.request_timeout = 120.0
        self.embedding_model = "nomic-embed-text"
        self._embedding_dim = None
        self._prompt_helper = OpenAIProvider()

    def init_provider(self, provider_cfg) -> None:
        self.provider_cfg = self._parse_config(provider_cfg)

    def _parse_config(self, provider_cfg) -> dict:
        if isinstance(provider_cfg, dict):
            conf_dict = provider_cfg
        else:
            path = assemble_project_path(provider_cfg)
            conf_dict = load_json(path)

        self.base_url = os.getenv("OLLAMA_BASE_URL", conf_dict.get(PROVIDER_SETTING_BASE_URL, self.base_url))
        self.llm_model = os.getenv("OLLAMA_CHAT_MODEL", conf_dict.get(PROVIDER_SETTING_COMP_MODEL, self.llm_model))
        self.embedding_model = os.getenv("OLLAMA_EMBED_MODEL", conf_dict.get(PROVIDER_SETTING_EMB_MODEL, self.embedding_model))
        self.request_timeout = float(os.getenv("OLLAMA_TIMEOUT", conf_dict.get(PROVIDER_SETTING_TIMEOUT, self.request_timeout)))

        if not self.llm_model:
            raise ValueError("Ollama provider requires 'comp_model' in its config.")
        if not self.embedding_model:
            raise ValueError("Ollama provider requires 'emb_model' in its config.")

        return conf_dict

    def _request_json(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)

    def _request_json_with_retry(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        last_error = None
        for attempt in range(self.retries):
            try:
                return self._request_json(endpoint, payload)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as error:
                last_error = error
                if attempt + 1 < self.retries:
                    time.sleep(2)

        raise last_error

    def _messages_to_ollama(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ollama_messages: List[Dict[str, Any]] = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", [])

            if isinstance(content, str):
                ollama_messages.append({"role": role, "content": content})
                continue

            text_parts: List[str] = []
            image_parts: List[str] = []

            for item in content:
                item_type = item.get("type")
                if item_type == "text":
                    text = item.get("text", "")
                    if text.strip():
                        text_parts.append(text)
                elif item_type == "image_url":
                    image_url = item.get("image_url", {})
                    image_value = image_url.get("url", "")
                    if image_value.startswith("data:") and "," in image_value:
                        image_value = image_value.split(",", 1)[1]
                    if image_value:
                        image_parts.append(image_value)

            payload: Dict[str, Any] = {"role": role, "content": "\n\n".join(text_parts).strip()}
            if image_parts:
                payload["images"] = image_parts

            ollama_messages.append(payload)

        return ollama_messages

    def create_completion(
        self,
        messages: List[Dict[str, str]],
        model: str | None = None,
        temperature: float = config.temperature,
        seed: int = config.seed,
        max_tokens: int = config.max_tokens,
    ) -> Tuple[str, Dict[str, int]]:

        if model is None:
            model = self.llm_model

        if config.debug_mode:
            logger.debug(f"Creating Ollama chat completion with model {model}, temperature {temperature}, max_tokens {max_tokens}")
        else:
            logger.write(f"Requesting {model} completion...")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": self._messages_to_ollama(messages),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if seed is not None:
            payload["options"]["seed"] = seed

        response = self._request_json_with_retry("/api/chat", payload)

        message = response.get("message", {}).get("content", "")
        info = {
            "input_tokens": int(response.get("prompt_eval_count", 0) or 0),
            "output_tokens": int(response.get("eval_count", 0) or 0),
            "total_tokens": int(response.get("prompt_eval_count", 0) or 0) + int(response.get("eval_count", 0) or 0),
        }

        logger.write(f"Response received from {model}.")
        return message, info

    async def create_completion_async(
        self,
        messages: List[Dict[str, str]],
        model: str | None = None,
        temperature: float = config.temperature,
        seed: int = config.seed,
        max_tokens: int = config.max_tokens,
    ) -> Tuple[str, Dict[str, int]]:
        return await asyncio.to_thread(
            self.create_completion,
            messages,
            model,
            temperature,
            seed,
            max_tokens,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []

        for text in texts:
            payload = {
                "model": self.embedding_model,
                "input": text,
            }
            try:
                response = self._request_json_with_retry("/api/embed", payload)
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    fallback_payload = {
                        "model": self.embedding_model,
                        "prompt": text,
                    }
                    response = self._request_json_with_retry("/api/embeddings", fallback_payload)
                else:
                    raise

            embedding = response.get("embedding")
            if embedding is None:
                embeddings_list = response.get("embeddings")
                if isinstance(embeddings_list, list) and len(embeddings_list) > 0:
                    embedding = embeddings_list[0]
            if embedding is None:
                raise ValueError("Ollama embedding response did not contain an embedding vector.")

            embeddings.append(embedding)

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

    def get_embedding_dim(self) -> int:
        if self._embedding_dim is None:
            self._embedding_dim = len(self.embed_query("dimension probe"))
        return self._embedding_dim

    def assemble_prompt_tripartite(self, template_str: str = None, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return self._prompt_helper.assemble_prompt_tripartite(template_str=template_str, params=params)

    def assemble_prompt_paragraph(self, template_str: str = None, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return self._prompt_helper.assemble_prompt_paragraph(template_str=template_str, params=params)

    def assemble_prompt(self, template_str: str = None, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return self._prompt_helper.assemble_prompt(template_str=template_str, params=params)
