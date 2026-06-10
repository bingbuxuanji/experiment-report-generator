#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件系统基类 — 所有实验素材专用分析器遵循此接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class AnalyzedModule:
    """分析结果——一个硬件/软件模块"""
    name: str
    description: str = ''
    pins: List[tuple] = field(default_factory=list)   # [(port, pin, mode, desc)]
    functions: List[str] = field(default_factory=list)  # 函数名列表
    key_params: Dict[str, str] = field(default_factory=dict)  # {param: value}


@dataclass
class AnalysisResult:
    """统一的插件分析结果"""
    source_type: str = ''           # 'stm32', 'c51', 'python', 'circuit', etc.
    title_hint: str = ''            # 实验标题建议
    modules: List[AnalyzedModule] = field(default_factory=list)
    init_sequence: List[str] = field(default_factory=list)
    main_loop_summary: str = ''
    interrupts: List[dict] = field(default_factory=list)  # [{name, trigger, actions}]
    wiring_diagram: str = ''        # 接线图文本描述
    flowchart_mermaid: str = ''     # 自动推断的 Mermaid 代码
    peripheral_config: Dict = field(default_factory=dict)
    key_algorithms: List[str] = field(default_factory=list)
    raw_summary: str = ''           # 给 LLM 的结构化摘要


class BasePlugin(ABC):
    """所有插件的抽象基类"""

    # 插件元信息（子类必须覆盖）
    name: str = 'base'
    description: str = '基础插件'
    version: str = '1.0'
    # 支持的文件扩展名
    file_extensions: List[str] = []

    @abstractmethod
    def can_handle(self, source_dir: Path) -> bool:
        """判断是否能处理该源码目录"""
        ...

    @abstractmethod
    def analyze(self, source_dir: Path) -> AnalysisResult:
        """分析源码目录，返回结构化结果"""
        ...

    def get_llm_context(self, result: AnalysisResult) -> str:
        """将分析结果转换为 LLM 可理解的结构化文本"""
        ctx = []
        ctx.append(f'[插件: {self.name}] 检测到 {result.source_type} 项目')
        if result.title_hint:
            ctx.append(f'实验标题建议: {result.title_hint}')
        if result.init_sequence:
            ctx.append(f'初始化流程: {" → ".join(result.init_sequence)}')
        if result.interrupts:
            for isr in result.interrupts:
                ctx.append(f'中断服务: {isr["name"]} — {isr.get("trigger","")}')
                for act in isr.get('actions', []):
                    ctx.append(f'  · {act}')
        if result.wiring_diagram:
            ctx.append(f'接线信息:\n{result.wiring_diagram}')
        if result.flowchart_mermaid:
            ctx.append(f'建议流程图(Mermaid):\n```mermaid\n{result.flowchart_mermaid}\n```')
        if result.peripheral_config:
            ctx.append(f'外设配置: {result.peripheral_config}')
        return '\n'.join(ctx)


class PluginRegistry:
    """插件注册表"""

    def __init__(self):
        self._plugins: List[BasePlugin] = []

    def register(self, plugin: BasePlugin):
        self._plugins.append(plugin)

    def find_plugin(self, source_dir: Path) -> Optional[BasePlugin]:
        """找到第一个能处理该目录的插件"""
        for p in self._plugins:
            if p.can_handle(source_dir):
                return p
        return None

    def list_plugins(self) -> List[BasePlugin]:
        return self._plugins
