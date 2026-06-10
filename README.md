# 实验报告自动生成引擎 v3.0

通用 LLM 驱动的实验报告批量生成工具。支持任意学科，自动解析 Word 模板，通过大模型理解非规范素材，生成完整实验报告并嵌入 Mermaid 流程图。

## 快速开始

```bash
# 1. 安装依赖
pip install python-docx

# 2. 配置 AI 服务（四选一，详见下方 LLM 配置）
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 运行
python generate_reports_v3.py \
    --name 张三 --id 2024102001 \
    --template template.docx \
    --materials ./实验素材
```

Windows 用户可直接双击 `生成报告.bat`。

## LLM 配置

### 方式一：Claude API（推荐）

```env
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

获取: [https://console.anthropic.com/](https://console.anthropic.com/)

### 方式二：OpenAI 兼容 API

```env
# .env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # 可替换为任何兼容 endpoint
```

### 方式三：DeepSeek API

```env
# .env
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

获取: [https://platform.deepseek.com/](https://platform.deepseek.com/)

DeepSeek 同时兼容 Anthropic API 格式，也可通过 Claude 客户端接入：

```env
ANTHROPIC_API_KEY=sk-your-deepseek-key
CLAUDE_BASE_URL=https://api.deepseek.com/anthropic
CLAUDE_MODEL=deepseek-v4-pro
```

### 方式四：本地 Ollama（免费）

```bash
# 安装 Ollama
# https://ollama.com/download
ollama pull qwen2.5:7b
```

```env
# .env
OLLAMA_MODEL=qwen2.5:7b
```

### 离线模式

未配置 AI 服务时，系统自动降级为离线模式——通过源码分析插件生成报告框架，需手动补充部分内容。

```bash
python generate_reports_v3.py ... --no-llm
```

## 架构

```
generate_reports_v3.py         ← CLI 入口
├── template_parser.py         ← 解析任意 .docx 模板
├── llm_client.py              ← Claude / OpenAI / DeepSeek / Ollama 统一接口
├── content_generator.py       ← LLM 生成报告 + Mermaid 流程图
├── tool_chain.py              ← docx 组装 + 图片嵌入
├── console_util.py            ← 控制台美化
└── plugins/                   ← 可扩展源码分析器
    ├── base.py                ← 插件基类
    └── stm32_analyzer.py      ← STM32 嵌入式源码分析
```

## 用法

### 通用模式（LLM 理解非规范素材）

```bash
python generate_reports_v3.py \
    --name 张三 --id 2024102001 \
    --template template.docx \
    --materials ./实验素材
```

素材文件夹可以是任意格式：txt、pdf 摘录、代码、笔记、截图描述等，LLM 会自动理解。

### 源码分析模式（启用插件）

```bash
python generate_reports_v3.py \
    --name 李四 --id 2024102002 \
    --template template.docx \
    --source ./stm32_project
```

系统自动检测项目类型并调用对应插件（当前支持 STM32 标准库项目）。

### 批量模式（多个实验一次生成）

```bash
python generate_reports_v3.py \
    --name 王五 --id 2024102003 \
    --template template.docx \
    --exp "GPIO应用实验:./materials/gpio" \
    --exp "TIM应用实验:./materials/tim" \
    --exp "USART应用实验:./materials/usart"
```

每个 `--exp` 用 `标题:路径` 格式，可混合素材文件夹和源码目录。

### LLM 缓存模式

LLM 生成的内容会自动缓存为 `llm_cache_*.txt` 文件。修改缓存后运行 `--no-llm` 即可重新组装报告，无需重复调用 API。

## 命令参考

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--name` | 学生姓名 | 必填 |
| `--id` | 学号 | 必填 |
| `--template` | Word 模板路径 | 必填 |
| `--materials` | 实验素材文件夹 | 可选 |
| `--source` | 源码项目文件夹 | 可选 |
| `--exp` | 批量模式（可多次指定） | 可选 |
| `--llm` | AI 后端: claude/openai/deepseek/ollama/auto | auto |
| `--llm-model` | 指定模型名 | 自动 |
| `--no-llm` | 离线模式 | false |
| `--output` | 输出目录 | 当前目录 |
| `--extra-prompt` | 附加给 LLM 的指令 | 空 |

## 模板要求

任意 .docx 文件，系统自动解析结构。建议模板包含：

- 封面（学院、专业、姓名等字段）
- 基本信息表（实验项目名称、学号、日期等）
- 内容区（实验目的、原理、步骤等章节）

系统会自动识别占位符和需要填充的单元格。

## 素材文件夹

支持任意格式的素材：

```
实验素材/
├── 实验指导书.pdf      # PDF
├── 实验笔记.txt        # 文本笔记
├── 参考代码/           # 代码目录
├── 数据.xlsx           # 表格
└── 实验照片.png        # 图片
```

LLM 会尽力理解所有文本内容。

## 扩展插件

在 `plugins/` 下创建 `.py` 文件，继承 `BasePlugin`：

```python
from plugins.base import BasePlugin, AnalysisResult

class MyAnalyzer(BasePlugin):
    name = 'my_analyzer'
    description = '我的分析器'
    file_extensions = ['.xxx']

    def can_handle(self, source_dir: Path) -> bool:
        return any(source_dir.rglob('*.xxx'))

    def analyze(self, source_dir: Path) -> AnalysisResult:
        # 分析逻辑
        return AnalysisResult(...)
```

## 依赖

- Python >= 3.8
- python-docx
- 联网（Mermaid 流程图渲染需访问 mermaid.ink）

## License

MIT
