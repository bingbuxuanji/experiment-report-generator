#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 客户端 - 统一接口支持多后端（Claude / OpenAI / DeepSeek / Ollama）
自动从项目根目录 .env 文件加载配置
"""

import os, sys, json, urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict


def _load_dotenv():
    """从 .env 文件加载配置（不覆盖已有的环境变量）"""
    for loc in [Path(__file__).parent / '.env', Path('.') / '.env']:
        if not loc.exists():
            continue
        with open(loc, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
        break

_load_dotenv()


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = '',
                 temperature: float = 0.7, max_tokens: int = 4096) -> str:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


# ══════════════════════════════════════════════════
#  Anthropic Claude API
# ══════════════════════════════════════════════════

class ClaudeClient(LLMClient):
    """Anthropic Claude API / DeepSeek Anthropic-compatible endpoint
    DeepSeek 兼容端点: 设置 CLAUDE_BASE_URL=https://api.deepseek.com/anthropic
    """

    MODELS = ['claude-sonnet-4-6', 'claude-opus-4-7', 'claude-haiku-4-5-20251001']

    def __init__(self, api_key: str = '', model: str = 'claude-sonnet-4-6',
                 base_url: str = 'https://api.anthropic.com/v1'):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        self.model = model
        self.base_url = base_url

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: str = '',
                 temperature: float = 0.7, max_tokens: int = 4096) -> str:
        if not self.api_key:
            raise RuntimeError('Claude API key not configured. '
                               'Set ANTHROPIC_API_KEY env var or pass api_key parameter.')

        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }

        messages = [{'role': 'user', 'content': prompt}]
        body = {
            'model': self.model,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'messages': messages,
        }
        if system_prompt:
            body['system'] = system_prompt

        req = urllib.request.Request(
            f'{self.base_url}/messages',
            data=json.dumps(body).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            data = json.loads(resp.read())
            return data['content'][0]['text']
        except Exception as e:
            raise RuntimeError(f'Claude API error: {e}')


# ══════════════════════════════════════════════════
#  OpenAI API (also works with compatible proxies)
# ══════════════════════════════════════════════════

class OpenAIClient(LLMClient):
    """OpenAI API / Azure OpenAI / DeepSeek / any OpenAI-compatible endpoint"""

    def __init__(self, api_key: str = '', model: str = 'gpt-4o',
                 base_url: str = 'https://api.openai.com/v1'):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self.model = model
        self.base_url = base_url

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: str = '',
                 temperature: float = 0.7, max_tokens: int = 4096) -> str:
        if not self.api_key:
            raise RuntimeError('OpenAI API key not configured.')

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        body = {
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }

        req = urllib.request.Request(
            f'{self.base_url}/chat/completions',
            data=json.dumps(body).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            data = json.loads(resp.read())
            return data['choices'][0]['message']['content']
        except Exception as e:
            raise RuntimeError(f'OpenAI API error: {e}')


# ══════════════════════════════════════════════════
#  DeepSeek API (OpenAI-compatible & Anthropic-compatible)
# ══════════════════════════════════════════════════

class DeepSeekClient(OpenAIClient):
    """DeepSeek API — OpenAI-compatible 接口，优先使用 DEEPSEEK_* 环境变量"""

    def __init__(self, api_key: str = '', model: str = 'deepseek-v4-pro',
                 base_url: str = 'https://api.deepseek.com'):
        super().__init__(
            api_key=api_key or os.environ.get('DEEPSEEK_API_KEY', os.environ.get('OPENAI_API_KEY', '')),
            model=model or os.environ.get('DEEPSEEK_MODEL', 'deepseek-v4-pro'),
            base_url=base_url or os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
        )


# ══════════════════════════════════════════════════
#  Ollama (local)
# ══════════════════════════════════════════════════

class OllamaClient(LLMClient):
    """Local Ollama instance"""

    def __init__(self, model: str = 'qwen2.5:7b', base_url: str = 'http://localhost:11434'):
        self.model = model
        self.base_url = base_url

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f'{self.base_url}/api/tags', method='GET')
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception:
            return False

    def generate(self, prompt: str, system_prompt: str = '',
                 temperature: float = 0.7, max_tokens: int = 4096) -> str:
        body = {
            'model': self.model,
            'prompt': prompt,
            'system': system_prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            },
        }
        req = urllib.request.Request(
            f'{self.base_url}/api/generate',
            data=json.dumps(body).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            data = json.loads(resp.read())
            return data.get('response', '')
        except Exception as e:
            raise RuntimeError(f'Ollama error: {e}')


# ══════════════════════════════════════════════════
#  工厂函数
# ══════════════════════════════════════════════════

def create_llm_client(backend: str = 'auto', **kwargs) -> LLMClient:
    """创建 LLM 客户端。backend: 'claude'|'openai'|'deepseek'|'ollama'|'auto'"""
    if backend == 'claude' or (backend == 'auto' and os.environ.get('ANTHROPIC_API_KEY')):
        c = ClaudeClient(
            api_key=kwargs.get('api_key', os.environ.get('ANTHROPIC_API_KEY', '')),
            model=kwargs.get('model', os.environ.get('CLAUDE_MODEL', 'claude-sonnet-4-6')),
            base_url=kwargs.get('base_url', os.environ.get('CLAUDE_BASE_URL', 'https://api.anthropic.com/v1'))
        )
        if c.is_available():
            return c
        if backend == 'claude':
            raise RuntimeError('ANTHROPIC_API_KEY 未设置')

    if backend == 'openai' or (backend == 'auto' and os.environ.get('OPENAI_API_KEY')):
        c = OpenAIClient(
            api_key=kwargs.get('api_key', os.environ.get('OPENAI_API_KEY', '')),
            model=kwargs.get('model', os.environ.get('OPENAI_MODEL', 'gpt-4o')),
            base_url=kwargs.get('base_url', os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1'))
        )
        if c.is_available():
            return c
        if backend == 'openai':
            raise RuntimeError('OPENAI_API_KEY 未设置')

    if backend == 'deepseek' or (backend == 'auto' and (
            os.environ.get('DEEPSEEK_API_KEY') or
            (os.environ.get('ANTHROPIC_API_KEY') and 'deepseek' in os.environ.get('CLAUDE_BASE_URL', '')) or
            (os.environ.get('OPENAI_API_KEY') and 'deepseek' in os.environ.get('OPENAI_BASE_URL', '')))):
        c = DeepSeekClient(
            api_key=kwargs.get('api_key', os.environ.get('DEEPSEEK_API_KEY',
                os.environ.get('OPENAI_API_KEY', os.environ.get('ANTHROPIC_API_KEY', '')))),
            model=kwargs.get('model', os.environ.get('DEEPSEEK_MODEL', 'deepseek-v4-pro')),
            base_url=kwargs.get('base_url', os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'))
        )
        if c.is_available():
            return c
        if backend == 'deepseek':
            raise RuntimeError('DeepSeek API Key 未设置（DEEPSEEK_API_KEY 或 OPENAI_API_KEY）')

    if backend == 'ollama' or backend == 'auto':
        c = OllamaClient(
            model=kwargs.get('model', os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b')),
            base_url=kwargs.get('base_url', os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434'))
        )
        if c.is_available():
            return c
        if backend == 'ollama':
            raise RuntimeError('Ollama 未运行，请先执行 ollama serve')

    if backend == 'auto':
        raise RuntimeError(
            '没有可用的 AI 服务。请选择以下任一方式：\n'
            '  1. 运行 setup.bat 配置向导\n'
            '  2. 创建 .env 文件设置 API Key\n'
            '  3. 使用 --no-llm 进入离线模式\n'
            '  支持: Claude / OpenAI / DeepSeek / Ollama'
        )
    raise ValueError(f'未知后端: {backend}')
