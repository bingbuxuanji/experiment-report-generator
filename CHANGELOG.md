# Changelog

## [1.0.1] — 2026-06-10

### 新增
- DeepSeek API 作为一等 LLM 后端（`--llm deepseek`），同时兼容 OpenAI 与 Anthropic API 格式
- 新增 `DeepSeekClient`，优先读取 `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL` 环境变量
- `setup.py` 配置向导新增 DeepSeek 选项，支持 deepseek-v4-pro / deepseek-v4-flash 模型选择
- `.env.example` 新增 DeepSeek 完整配置说明
- `ClaudeClient` 支持通过 `CLAUDE_BASE_URL=https://api.deepseek.com/anthropic` 接入 DeepSeek

### 变更
- 默认模型从 `deepseek-chat`（将于 2026/07/24 弃用）升级为 `deepseek-v4-pro`
- LLM 配置由三种扩展为四种（Claude / OpenAI / DeepSeek / Ollama）

## [1.0.0] — 2025-12-25

### 新增
- 实验报告自动生成引擎 v3.0 初始发布
- LLM 驱动的内容生成（Claude / OpenAI / Ollama）
- Word 模板解析与组装
- Mermaid 流程图生成与渲染
- STM32 源码分析插件
- LLM 缓存模式
- 批量实验生成
