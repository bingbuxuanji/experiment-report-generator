#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验报告自动生成引擎 v3.0 — 通用 LLM 驱动版
=============================================
架构:
  1. 模板解析器 → 理解任何 .docx 模板结构
  2. LLM 客户端 → 统一接口支持 Claude/OpenAI/Ollama
  3. 内容生成器 → LLM 解析非规范素材，生成报告各节和 Mermaid 流程图
  4. 工具链 → Mermaid→PNG 渲染 + docx 组装
  5. 插件系统 → 可选的外挂源码分析器 (STM32/51/...)

用法:
  # 通用模式：传入模板 + 素材文件夹
  python generate_reports_v3.py --name 张三 --id 2024102001 \
      --template template.docx --materials ./实验素材 --llm claude

  # 源码分析模式：启用 STM32 插件
  python generate_reports_v3.py --name 李四 --id 2024102002 \
      --template template.docx --source ./src_project --plugin stm32

  # 批量模式：多个实验一次生成
  python generate_reports_v3.py --name 王五 --id 2024102003 \
      --template template.docx \
      --exp "GPIO:./materials/exp1" \
      --exp "TIM:./materials/exp2" \
      --exp "USART:./materials/exp3"

依赖:
  pip install python-docx
"""

import os, sys, re, shutil, argparse, textwrap
from pathlib import Path
from typing import Dict, List, Optional

# 添加当前目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from template_parser import parse_template, describe_for_llm
from llm_client import create_llm_client, LLMClient
from content_generator import (
    collect_materials, generate_report_content, render_mermaid, parse_llm_response
)
from tool_chain import assemble_report
from plugins.base import PluginRegistry, BasePlugin, AnalysisResult
from console_util import title as ctitle, section, step, ok, warn, fail, info, item, divider, done as cdone


# ══════════════════════════════════════════════════
#  插件加载
# ══════════════════════════════════════════════════

def load_plugins() -> PluginRegistry:
    """自动发现并加载 plugins 目录下的所有插件"""
    registry = PluginRegistry()
    plugins_dir = Path(__file__).parent / 'plugins'
    if not plugins_dir.exists():
        return registry

    for py_file in sorted(plugins_dir.glob('*.py')):
        if py_file.name.startswith('_') or py_file.name == 'base.py':
            continue
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                f'plugins.{py_file.stem}', str(py_file))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BasePlugin) and
                    attr is not BasePlugin):
                    plugin = attr()
                    registry.register(plugin)
        except Exception as e:
            info(f'加载插件 {py_file.name} 失败: {e}')
    return registry


# ══════════════════════════════════════════════════
#  单实验处理
# ══════════════════════════════════════════════════

def process_single_experiment(
    llm: LLMClient,
    template_path: str,
    student_info: Dict[str, str],
    materials_path: Optional[str],
    source_path: Optional[str],
    plugin_registry: Optional[PluginRegistry],
    output_dir: str,
    exp_label: str = '',
    extra_prompt: str = '',
    use_llm: bool = True,
) -> str:
    """处理单个实验：模板→分析→生成→组装"""

    # Step 1: parse template
    step(1, '解析模板结构')
    template = parse_template(template_path)
    info(f'识别到 {len(template.tables)} 个表格, {len(template.placeholders)} 个占位符')

    # Step 2: collect materials / analyze source
    materials_text = ''
    plugin_context = ''
    title_hint = ''
    plugin_mermaid = ''

    if materials_path and Path(materials_path).exists():
        step(2, '收集实验素材')
        materials_text = collect_materials(materials_path)
        info(f'素材总计 {len(materials_text)} 字符')

    if source_path and plugin_registry:
        if not materials_text:
            step(2, '源码分析')
        src_dir = Path(source_path)
        plugin = plugin_registry.find_plugin(src_dir)
        if plugin:
            result = plugin.analyze(src_dir)
            plugin_context = plugin.get_llm_context(result)
            title_hint = result.title_hint
            plugin_mermaid = result.flowchart_mermaid
            ok(f'插件 {plugin.name}: {len(result.modules)} 个模块')
            if title_hint:
                info(f'标题: {title_hint}')
        else:
            warn('未找到适用的源码分析插件')

    # Step 3: generate content
    step(3, '生成报告内容')
    cache_path = Path(f'llm_cache_{exp_label}.txt')
    if cache_path.exists():
        info(f'使用缓存: {cache_path.name}')
        cached_response = cache_path.read_text(encoding='utf-8')
        content = parse_llm_response(cached_response)
    elif use_llm:
        content = generate_report_content(
            llm, template, student_info,
            materials_text, plugin_context, extra_prompt
        )
    else:
        content = generate_from_plugin(template, plugin_context, title_hint, plugin_mermaid)

    title_text = content.get('title', exp_label)
    ok(f'标题: {title_text[:60]}')

    # Step 4: render flowchart
    step(4, '渲染流程图')
    flowchart_dir = Path(output_dir) / 'flowcharts'
    flowchart_dir.mkdir(parents=True, exist_ok=True)
    png_name = f'flow_{sanitize_filename(exp_label)}.png'
    png_path = flowchart_dir / png_name

    mermaid_code = content.get('mermaid', '')
    png_ok = render_mermaid(mermaid_code, str(png_path))
    if png_ok:
        ok(f'{png_name} ({png_path.stat().st_size // 1024} KB)')
    else:
        warn('流程图渲染失败，已嵌入代码文本')
        png_path = None

    # Step 5: assemble docx
    step(5, '组装 Word 文档')
    safe_title = sanitize_filename(title_text)
    filename = f'{student_info.get("id","")}{student_info.get("name","")}《{safe_title}》.docx'
    out_path = os.path.join(output_dir, filename)

    assemble_report(
        template, content,
        str(png_path) if png_path else None,
        student_info, out_path
    )

    size_kb = os.path.getsize(out_path) // 1024
    ok(f'{filename} ({size_kb} KB)')
    return out_path


def generate_from_plugin(template, plugin_context: str,
                        title_hint: str = '',
                        mermaid_code: str = '') -> Dict[str, str]:
    """无 LLM 时的降级方案：使用插件分析结果生成基础内容"""
    title = title_hint or '实验报告'
    return {
        'title': title,
        'purpose': '（未启用 LLM，以下为插件自动分析结果，请手动完善实验目的）',
        'content': plugin_context or '（无插件分析结果）',
        'principle': '（请根据实验指导书手动填写实验原理与方法）',
        'equipment': '① NANO STM32F1开发板  ② 相关外设模块  ③ USB转串口模块  ④ 杜邦线若干  ⑤ 计算机',
        'steps': '（请手动填写实验步骤）',
        'results': '（请手动填写实验结果与思考）',
        'mermaid': mermaid_code or '',
    }


def sanitize_filename(s: str) -> str:
    """清理文件名"""
    s = s.replace('：', '').replace('（', '(').replace('）', ')')
    s = re.sub(r'[<>:"/\\|?*]', '', s)[:80]
    return s.strip()


# ══════════════════════════════════════════════════
#  CLI 入口
# ══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='实验报告自动生成引擎 v3.0 — LLM 驱动通用版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        示例:
          # 单实验、单素材文件夹
          python generate_reports_v3.py --name 张三 --id 2024102001 \\
              --template template.docx --materials ./实验素材

          # 源码分析（启用 STM32 插件）
          python generate_reports_v3.py --name 李四 --id 2024102002 \\
              --template template.docx --source ./stm32_project

          # 批量：多个实验
          python generate_reports_v3.py --name 王五 --id 2024102003 \\
              --template template.docx \\
              --exp "GPIO应用实验:./materials/gpio" \\
              --exp "TIM应用实验:./materials/tim"

          # 指定 LLM 后端
          python generate_reports_v3.py --name 赵六 --id 2024102004 \\
              --template template.docx --materials ./素材 --llm ollama

        LLM 配置:
          Claude:   export ANTHROPIC_API_KEY=sk-ant-...
          OpenAI:   export OPENAI_API_KEY=sk-...
          DeepSeek: export DEEPSEEK_API_KEY=sk-...  (兼容 OpenAI/Anthropic)
          Ollama:   ollama serve (默认 http://localhost:11434)
        """)
    )

    # 学生信息
    parser.add_argument('--name', help='学生姓名')
    parser.add_argument('--id', help='学号')
    parser.add_argument('--class-name', default='24自动化1班', help='班级')
    parser.add_argument('--major', default='自动化', help='专业')
    parser.add_argument('--college', default='智能制造与信息工程学院', help='学院')
    parser.add_argument('--course', default='单片机原理与应用', help='课程')
    parser.add_argument('--semester', default='2025—2026年 第1学期', help='学期')
    parser.add_argument('--date', default='2025年12月25日', help='实验日期')
    parser.add_argument('--location', default='1312', help='实验地点')

    # 核心参数
    parser.add_argument('--template', required=True, help='Word 模板路径 (.docx)')
    parser.add_argument('--materials', help='实验素材文件夹路径')
    parser.add_argument('--source', help='源码文件夹（启用插件分析，和 --materials 二选一或共用）')
    parser.add_argument('--plugin', help='指定插件名（可选，默认自动检测）')
    parser.add_argument('--exp', action='append', dest='experiments',
                        help='批量模式：格式 "标题:素材路径" 或 "标题:源码路径"，可多次指定')

    # LLM 参数
    parser.add_argument('--llm', default='auto',
                        choices=['auto', 'claude', 'openai', 'deepseek', 'ollama'],
                        help='LLM 后端选择 (default: auto)')
    parser.add_argument('--llm-model', help='指定模型名（如 claude-sonnet-4-6）')
    parser.add_argument('--llm-key', help='API Key（覆盖环境变量）')
    parser.add_argument('--llm-base-url', help='API Base URL（自定义端点）')
    parser.add_argument('--no-llm', action='store_true', help='离线模式：不使用 LLM')

    # 输出
    parser.add_argument('--output', default='.', help='输出目录')
    parser.add_argument('--extra-prompt', default='', help='附加给 LLM 的指令')
    parser.add_argument('--interactive', action='store_true', help='交互模式')

    args = parser.parse_args()

    # ── 交互模式 ──
    if args.interactive:
        print('\n=== 学生信息 ===')
        args.name = input(f'  姓名 [{args.name or ""}]: ').strip() or args.name
        args.id = input(f'  学号 [{args.id or ""}]: ').strip() or args.id
        args.class_name = input(f'  班级 [{args.class_name}]: ').strip() or args.class_name
        args.major = input(f'  专业 [{args.major}]: ').strip() or args.major
        print()

    if not args.name or not args.id:
        parser.error('--name 和 --id 为必填参数')

    student_info = {
        'name': args.name, 'id': args.id,
        'class_name': args.class_name, 'major': args.major,
        'college': args.college, 'course': args.course,
        'semester': args.semester, 'date': args.date,
        'location': args.location,
    }

    # ── 验证模板 ──
    template_path = Path(args.template)
    if not template_path.exists():
        print(f'[错误] 模板文件不存在: {args.template}')
        sys.exit(1)

    # ── Init LLM ──
    llm = None
    if not args.no_llm:
        llm_kwargs = {}
        if args.llm_key: llm_kwargs['api_key'] = args.llm_key
        if args.llm_model: llm_kwargs['model'] = args.llm_model
        if args.llm_base_url: llm_kwargs['base_url'] = args.llm_base_url
        try:
            llm = create_llm_client(args.llm, **llm_kwargs)
        except RuntimeError as e:
            warn('AI 服务未配置，使用离线模式')
            info('运行 setup.bat 配置 AI，或查看 使用说明书.md')
            llm = None

    # ── Load plugins ──
    registry = load_plugins()

    # ── 输出目录 ──
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 处理实验 ──
    if args.experiments:
        # Batch mode
        ctitle(f'批量生成 - {len(args.experiments)} 个实验')
        info(f'模板: {Path(args.template).name}')
        info(f'学生: {args.name}  {args.id}')
        info(f'输出: {output_dir.absolute()}')

        for ei, exp_spec in enumerate(args.experiments, 1):
            parts = exp_spec.split(':', 1)
            label = parts[0]
            path = parts[1] if len(parts) > 1 else ''

            section(f'实验 {ei}/{len(args.experiments)}: {label}')

            p = Path(path)
            if not p.exists():
                fail(f'路径不存在: {path}，跳过')
                continue

            is_source = bool(list(p.rglob('*.c'))) if p.is_dir() else False

            process_single_experiment(
                llm=llm, template_path=str(template_path),
                student_info=student_info,
                materials_path=None if is_source else path,
                source_path=path if is_source else None,
                plugin_registry=registry,
                output_dir=str(output_dir),
                exp_label=label,
                extra_prompt=args.extra_prompt,
                use_llm=llm is not None,
            )
    else:
        # Single experiment mode
        ctitle(f'实验报告生成器 v3.0')
        info(f'学生: {args.name}  {args.id}    模板: {Path(args.template).name}')
        info(f'输出: {output_dir.absolute()}')

        process_single_experiment(
            llm=llm, template_path=str(template_path),
            student_info=student_info,
            materials_path=args.materials,
            source_path=args.source,
            plugin_registry=registry,
            output_dir=str(output_dir),
            extra_prompt=args.extra_prompt,
            use_llm=llm is not None,
        )

    cdone(f'完成！文件已保存到: {output_dir.absolute()}')


if __name__ == '__main__':
    main()
