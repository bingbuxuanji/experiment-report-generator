# -*- coding: utf-8 -*-
"""实验报告生成器 - 首次配置向导"""

import os, sys, subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
ENV_FILE = PROJECT_DIR / '.env'


def print_header():
    print()
    print("=" * 50)
    print("  实验报告自动生成器 - 首次配置向导")
    print("=" * 50)
    print()
    print("本工具可以用 AI 自动生成实验报告。")
    print("选择一种 AI 服务配置即可开始使用。")
    print()


def check_python():
    print("[1/3] 检查环境...")
    print(f"      Python: {sys.version.split()[0]}")
    print(f"      路径: {sys.executable}")

    # 检查 python-docx
    try:
        import docx
        print("      python-docx: 已安装")
    except ImportError:
        print("      python-docx: 未安装，正在安装...")
        rc = subprocess.call(
            [sys.executable, '-m', 'pip', 'install', 'python-docx', '-q'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if rc != 0:
            print("      安装失败，尝试清华镜像...")
            subprocess.call(
                [sys.executable, '-m', 'pip', 'install', 'python-docx', '-q',
                 '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        try:
            import docx
            print("      python-docx: 安装成功")
        except ImportError:
            print("      [警告] 安装失败，请手动执行: pip install python-docx")
    print()


def check_existing():
    if ENV_FILE.exists():
        print("[2/3] 已有 .env 配置文件")
        ans = input("      是否重新配置? (y/N): ").strip().lower()
        if ans != 'y':
            print("      保持现有配置，跳过")
            return True
        ENV_FILE.unlink()
        print("      已删除旧配置")
    return False


def choose_backend():
    print("[2/3] 选择 AI 服务：")
    print()
    print("  [1] Claude API    - Anthropic Claude，效果好")
    print("  [2] OpenAI API    - ChatGPT 同款")
    print("  [3] DeepSeek API  - 国内可用，兼容 OpenAI/Anthropic 格式")
    print("  [4] 本地 Ollama    - 免费，无需联网")
    print("  [5] 跳过           - 离线模式")
    print()

    while True:
        choice = input("  请输入数字 (1-5): ").strip()
        if choice in ('1', '2', '3', '4', '5'):
            return choice
        print("  无效选项，请重新输入")


def setup_claude():
    print()
    print("  请打开 https://console.anthropic.com/ 获取 API Key")
    print("  格式: sk-ant-...")
    print()
    key = input("  粘贴 Key: ").strip()
    if not key:
        print("  未输入 Key，跳过")
        return
    ENV_FILE.write_text(f"ANTHROPIC_API_KEY={key}\n", encoding='utf-8')
    print("  [OK] Claude API 已配置")


def setup_openai():
    print()
    print("  请打开 https://platform.openai.com/ 获取 API Key")
    print("  格式: sk-...")
    print()
    key = input("  粘贴 Key: ").strip()
    if not key:
        print("  未输入 Key，跳过")
        return
    lines = [f"OPENAI_API_KEY={key}"]

    print()
    base = input("  如使用第三方代理，输入 Base URL (直接回车跳过): ").strip()
    if base:
        lines.append(f"OPENAI_BASE_URL={base}")

    ENV_FILE.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print("  [OK] OpenAI API 已配置")


def setup_deepseek():
    print()
    print("  请打开 https://platform.deepseek.com/ 获取 API Key")
    print("  格式: sk-...")
    print()
    key = input("  粘贴 Key: ").strip()
    if not key:
        print("  未输入 Key，跳过")
        return
    print()
    print("  可选模型:")
    print("    1. deepseek-v4-pro   (Pro 版，推荐)")
    print("    2. deepseek-v4-flash (Flash 版，更快)")
    model_choice = input("  选择模型 (默认 1): ").strip()
    model = 'deepseek-v4-flash' if model_choice == '2' else 'deepseek-v4-pro'
    lines = [
        f"DEEPSEEK_API_KEY={key}",
        f"DEEPSEEK_BASE_URL=https://api.deepseek.com",
        f"DEEPSEEK_MODEL={model}",
    ]
    ENV_FILE.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"  [OK] DeepSeek API 已配置 (模型: {model})")


def setup_ollama():
    print()
    print("  请确保 Ollama 已安装并运行")
    print("  下载: https://ollama.com/download")
    print("  常用模型: qwen2.5:7b / llama3.2 / mistral / deepseek-r1:7b")
    print()
    model = input("  模型名称 (默认 qwen2.5:7b): ").strip()
    if not model:
        model = "qwen2.5:7b"
    ENV_FILE.write_text(
        f"OLLAMA_MODEL={model}\n"
        f"OLLAMA_BASE_URL=http://localhost:11434\n",
        encoding='utf-8'
    )
    print(f"  [OK] Ollama 已配置 (模型: {model})")


def main():
    print_header()
    check_python()

    if check_existing():
        show_done()
        return

    choice = choose_backend()

    if choice == '1':
        setup_claude()
    elif choice == '2':
        setup_openai()
    elif choice == '3':
        setup_deepseek()
    elif choice == '4':
        setup_ollama()
    elif choice == '5':
        print("  [跳过] 将使用离线模式（功能受限）")

    show_done()


def show_done():
    print()
    print("[3/3] 配置完成")
    print()
    print("-" * 42)
    print("  快速开始:")
    print("    1. 双击 生成报告.bat")
    print("    2. 或命令行:")
    print("       python generate_reports_v3.py --help")
    print("-" * 42)
    print()
    print("  详细帮助: 使用说明书.md")
    print()
    input("按回车键退出...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n[错误] {e}")
        input("按回车键退出...")
