# -*- coding: utf-8 -*-
"""控制台输出美化工具 - 处理 Windows GBK 兼容 + 颜色"""

import sys, os

# 强制 UTF-8 输出（Windows 兼容）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    os.system('chcp 65001 >nul 2>&1')

# ANSI 颜色码
C = {
    'R': '\033[91m', 'G': '\033[92m', 'Y': '\033[93m', 'B': '\033[94m',
    'C': '\033[96m', 'W': '\033[97m', 'D': '\033[90m',
    'reset': '\033[0m', 'bold': '\033[1m',
}

# 如果输出不是终端（如重定向到文件），禁用颜色
if not sys.stdout.isatty():
    for k in C:
        C[k] = ''


def title(text: str):
    print(f'\n{C["C"]}{"="*60}{C["reset"]}')
    print(f'{C["bold"]}{text}{C["reset"]}')
    print(f'{C["C"]}{"="*60}{C["reset"]}')


def section(text: str):
    print(f'\n{C["G"]}--- {text} ---{C["reset"]}')


def step(num: int, text: str):
    print(f'  {C["Y"]}[{num}/5]{C["reset"]} {text}')


def ok(text: str):
    print(f'  {C["G"]}[OK]{C["reset"]} {text}')


def warn(text: str):
    print(f'  {C["Y"]}[WARN]{C["reset"]} {text}')


def fail(text: str):
    print(f'  {C["R"]}[FAIL]{C["reset"]} {text}')


def info(text: str):
    print(f'  {C["D"]}{text}{C["reset"]}')


def item(text: str):
    print(f'    {text}')


def divider():
    print(f'{C["D"]}{"-"*60}{C["reset"]}')


def done(text: str = '完成'):
    print(f'\n{C["G"]}{"="*60}{C["reset"]}')
    print(f'{C["bold"]}  {text}{C["reset"]}')
    print(f'{C["G"]}{"="*60}{C["reset"]}\n')
