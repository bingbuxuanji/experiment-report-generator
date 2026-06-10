#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容生成器 — 使用 LLM 从非规范实验素材生成报告各节内容 + Mermaid 流程图
"""

import base64, urllib.request, os
from pathlib import Path
from typing import Dict, Optional

from llm_client import LLMClient
from template_parser import TemplateStructure, describe_for_llm


def collect_materials(materials_dir: str) -> str:
    """从素材目录收集所有文本内容，拼接为 LLM 可读的字符串"""
    mp = Path(materials_dir)
    if not mp.exists():
        return ''

    parts = []
    for f in sorted(mp.rglob('*')):
        if f.is_dir():
            continue
        if f.suffix in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.ico', '.pdf',
                        '.exe', '.dll', '.obj', '.hex', '.lnp', '.uvopt', '.uvproj',
                        '.uvgui', '.lst', '.m51', '.build_log'}:
            continue
        try:
            text = f.read_text(encoding='utf-8', errors='ignore')
            if text.strip():
                # 截断过长的文件
                if len(text) > 8000:
                    text = text[:8000] + f'\n... [文件过长，已截断，原{len(text)}字符]'
                parts.append(f'=== {f.relative_to(mp)} ===\n{text}\n')
        except Exception:
            parts.append(f'=== {f.relative_to(mp)} ===\n[二进制文件，无法读取文本]\n')

    return '\n'.join(parts)


SYSTEM_PROMPT = """你是一位专业的大学实验报告撰写助手。用户会提供：
1. 实验报告模板的结构描述
2. 实验素材（可能包含：代码文件、笔记、参考文献、数据表格等，格式不规范，需要你理解）
3. 学生信息

你的任务是为实验报告的每个部分生成正式内容。要求：
- 语言：专业、准确、简洁
- 格式：按模板结构返回，使用 Marker 分隔：【实验标题】【实验目的】【实验内容】【实验原理与方法】【主要实验设备及器材】【实验步骤】【实验结果与思考】【流程图】
- 流程图：使用标准 Mermaid flowchart TD 语法
- 禁止编造具体数据（如温度=25°C），除非素材中有
- 禁止在报告中引用"素材中""根据代码"等元描述
- 章节编号使用"一、二、三、四、五、六"
"""

REPORT_PROMPT = """请根据以下信息，生成一份完整的实验报告内容。

## 模板结构
{template_desc}

## 学生信息
{student_info}

## 实验素材内容
{materials}

## 插件分析结果（如有）
{plugin_context}

---
请按照以下 Marker 分隔返回完整报告内容（每个 Marker 独占一行，后跟内容）：

【实验标题】
（课程对应的实验标题）

【实验目的】
1. ...
2. ...

【实验内容】
简要描述本实验做什么

【实验原理与方法】
（含硬件接线/软件流程图描述）

【主要实验设备及器材】
① ... ② ...

【实验步骤】
1. ...
2. ...

【实验结果与思考】
实验结果：...
实验思考：...

【流程图】
```mermaid
flowchart TD
    ...
```

注意：
- 流程图务必使用标准 Mermaid 语法，节点文本避免使用括号 ()，可用 <br/> 换行
- 实验设备要具体到型号和数量
- 实验步骤要具备可操作性
"""


def generate_report_content(
    llm: LLMClient,
    template: TemplateStructure,
    student_info: Dict[str, str],
    materials_text: str,
    plugin_context: str = '',
    extra_prompt: str = '',
) -> Dict[str, str]:
    """
    调用 LLM 生成报告内容。

    返回: {title, purpose, content, principle, equipment, steps, results, mermaid}
    """

    # 模板描述
    template_desc = describe_for_llm(template)

    # 学生信息
    student_str = '\n'.join(f'{k}: {v}' for k, v in student_info.items() if v)

    # 构建提示
    prompt = REPORT_PROMPT.format(
        template_desc=template_desc,
        student_info=student_str,
        materials=materials_text or '（未提供额外素材，请根据通用实验知识生成）',
        plugin_context=plugin_context or '（未启用源码分析插件）',
    )
    if extra_prompt:
        prompt += f'\n\n额外要求: {extra_prompt}'

    # 调用 LLM
    response = llm.generate(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.7, max_tokens=4096)

    # 解析 LLM 返回
    return parse_llm_response(response)


def parse_llm_response(response: str) -> Dict[str, str]:
    """解析 LLM 返回的 Marker 分隔内容"""
    import re

    result = {
        'title': '',
        'purpose': '',
        'content': '',
        'principle': '',
        'equipment': '',
        'steps': '',
        'results': '',
        'mermaid': '',
    }

    markers = {
        '实验标题': 'title',
        '实验目的': 'purpose',
        '实验内容': 'content',
        '实验原理与方法': 'principle',
        '主要实验设备及器材': 'equipment',
        '实验步骤': 'steps',
        '实验结果与思考': 'results',
        '流程图': 'mermaid',
    }

    for marker, key in markers.items():
        pattern = rf'【{marker}】\s*\n(.*?)(?=【(?:{"|".join(markers.keys())})\】|\Z)'
        m = re.search(pattern, response, re.DOTALL)
        if m:
            result[key] = m.group(1).strip()

    # 清洗 mermaid（只保留代码块内容）
    mmd = result['mermaid']
    if mmd:
        code_match = re.search(r'```(?:mermaid)?\s*\n?(.*?)```', mmd, re.DOTALL)
        if code_match:
            result['mermaid'] = code_match.group(1).strip()
        else:
            result['mermaid'] = mmd.strip()
        # 确保以 flowchart 开头
        if not result['mermaid'].startswith('flowchart') and not result['mermaid'].startswith('graph'):
            result['mermaid'] = 'flowchart TD\n' + result['mermaid']

    return result


def render_mermaid(mermaid_code: str, output_path: str) -> bool:
    """通过 mermaid.ink 渲染为 PNG"""
    if not mermaid_code.strip():
        return False
    mmd_bytes = mermaid_code.encode('utf-8')
    b64 = base64.urlsafe_b64encode(mmd_bytes).decode().strip('=')
    url = f'https://mermaid.ink/img/{b64}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=60)
        data = resp.read()
        if resp.status == 200 and len(data) > 2000:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(data)
            return True
    except Exception as e:
        print(f'    [Mermaid 渲染失败] {e}')
    return False
