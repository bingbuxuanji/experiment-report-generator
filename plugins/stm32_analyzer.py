#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STM32 源码分析插件 — 将 v2 的 CodeAnalyzer 封装为插件
"""
import re, sys
from pathlib import Path
from typing import List

# 允许从父目录导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.base import BasePlugin, AnalysisResult, AnalyzedModule
from generate_reports_v2 import CodeAnalyzer


class STM32AnalyzerPlugin(BasePlugin):
    name = 'stm32'
    description = 'STM32F10x / STM32F4xx 标准库源码分析器，自动提取引脚、中断、外设配置'
    version = '2.0'
    file_extensions = ['.c', '.h', '.uvproj', '.uvprojx']

    def can_handle(self, source_dir: Path) -> bool:
        """检查目录中是否包含 STM32 特征文件"""
        # 方法1: 查找 stm32f10x.h 或类似头文件引用
        c_files = list(source_dir.rglob('*.c'))
        for cf in c_files:
            try:
                content = cf.read_text(encoding='utf-8', errors='ignore')
                if 'stm32f10x.h' in content.lower() or 'STM32F10X' in content:
                    return True
                if re.search(r'stm32f\d+', content, re.IGNORECASE):
                    return True
            except Exception:
                pass
        # 方法2: 检查是否有标准库目录
        if (source_dir / 'Library').exists() and (source_dir / 'User').exists():
            return True
        return False

    def analyze(self, source_dir: Path) -> AnalysisResult:
        """使用 CodeAnalyzer 分析，转换为插件标准格式"""
        raw = CodeAnalyzer.analyze(str(source_dir))

        result = AnalysisResult(
            source_type=f'STM32 ({raw.get("chip_type", "unknown")})',
            title_hint=self._infer_title(raw),
            init_sequence=raw.get('main_calls', []),
            main_loop_summary=raw.get('main_loop_body', ''),
            interrupts=raw.get('isr_list', []),
            wiring_diagram=raw.get('wiring', ''),
            flowchart_mermaid=self._build_mermaid(raw),
            peripheral_config={**raw.get('timer_config', {}),
                               **raw.get('usart_config', {})},
        )

        # 转换模块
        for mod_name, mod in raw.get('modules', {}).items():
            am = AnalyzedModule(
                name=mod_name,
                description=mod.header_comment,
                pins=mod.pins,
                functions=[f.name for f in mod.funcs],
            )
            result.modules.append(am)

        # 构建 LLM 摘要
        result.raw_summary = self._build_summary(result, raw)
        return result

    def _infer_title(self, raw: dict) -> str:
        """推断实验标题"""
        proj = raw.get('project_name', '')
        title_map = {
            '按键控制LED': 'GPIO的应用实验——按键控制LED（输入输出综合）',
            '定时器定时中断': 'TIM的应用实验——定时器定时中断（基本定时）',
            '定时器外部时钟': 'TIM的应用实验——定时器外部时钟（输入捕获）',
            '串口发送': 'USART的应用实验——串口发送',
            '串口发送+接收': 'USART的应用实验——串口发送+接收',
        }
        for key, title in title_map.items():
            if key in proj:
                return title
        return proj

    def _build_mermaid(self, raw: dict) -> str:
        """生成 Mermaid 流程图"""
        from generate_reports_v2 import auto_generate_mermaid
        try:
            return auto_generate_mermaid(raw)
        except Exception:
            return ''

    def _build_summary(self, result: AnalysisResult, raw: dict) -> str:
        """生成给 LLM 的结构化文本摘要"""
        lines = []
        lines.append(f'## 源码分析结果 (STM32项目: {raw.get("project_name","")})')
        lines.append(f'芯片类型: {raw.get("chip_type","")}')

        # 模块
        lines.append('\n### 硬件模块')
        for mod in result.modules:
            pin_str = ', '.join(f'{p[0]}{p[1]}' for p in mod.pins)
            lines.append(f'- {mod.name}: {mod.description} (引脚: {pin_str or "无"})')

        # 初始化
        if result.init_sequence:
            lines.append('\n### 初始化流程')
            lines.append(' → '.join(result.init_sequence))

        # 中断
        if result.interrupts:
            lines.append('\n### 中断服务')
            for isr in result.interrupts:
                lines.append(f'- {isr["name"]}: {isr.get("trigger","")}')
                for a in isr.get('actions', []):
                    lines.append(f'  · {a}')

        # 外设
        if result.peripheral_config:
            lines.append('\n### 外设配置')
            for k, v in result.peripheral_config.items():
                lines.append(f'- {k}: {v}')

        # 接线
        if result.wiring_diagram:
            lines.append(f'\n### 硬件接线\n{result.wiring_diagram}')

        return '\n'.join(lines)
