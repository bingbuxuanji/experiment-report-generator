@echo off
chcp 65001 >nul
title 单片机实验报告生成器
echo ============================================
echo      单片机实验报告批量生成工具
echo      NANO STM32F1 实验报告自动生成
echo ============================================
echo.

REM ── 检查 Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.x
    pause & exit /b 1
)

REM ── 运行主脚本 ──
python "%~dp0generate_reports.py" %*
if %errorlevel% neq 0 (
    echo.
    echo [错误] 生成失败，请检查错误信息
)
pause
