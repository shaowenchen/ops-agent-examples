#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行服务入口 - Ops Agent SLO

此文件是命令行执行入口，负责：
1. 加载环境变量配置
2. 读取当前目录下的 input.txt 文件作为 data（不传递 key）
3. 调用 sla.py 中的编排逻辑

真实的业务编排逻辑在 sla.py 中定义
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console

console = Console()


def print_banner():
    """Print application banner"""
    banner = """
    ===============================================================
    
            Ops Agent SLO
            Service Level Objective Monitoring
    
    ===============================================================
    """
    console.print(banner, style="bold cyan")


def main():
    """Main entry point - reads input.txt and executes sla.py"""
    # Load .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Also try to load from .env file in current directory and project root
    env_files = [
        os.path.join(os.path.dirname(__file__), '.env'),
        '.env',
        os.path.expanduser('~/.env')
    ]
    for env_file in env_files:
        if os.path.exists(env_file):
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file, override=False)
            except:
                pass
            break
    
    print_banner()
    
    # 读取当前目录下的 input.txt 文件作为 data
    input_file = os.path.join(os.path.dirname(__file__), 'input.txt')
    input_data = None
    
    if os.path.exists(input_file):
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                input_data = f.read().strip()
            console.print(f"[green]✓[/green] Loaded data from input.txt ({len(input_data)} characters)")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to read input.txt: {e}[/yellow]")
            console.print("[yellow]Continuing without input data...[/yellow]")
    else:
        console.print(f"[yellow]Warning: input.txt not found at {input_file}[/yellow]")
        console.print("[yellow]Continuing without input data...[/yellow]")
    
    console.print("\n[cyan]Executing sla.py...[/cyan]\n")
    
    # Import and execute sla.py
    try:
        from sla import main as sla_main
        # 传递 input.txt 的内容作为 data，不传递 key
        sla_main(data=input_data, key=None)
    except ImportError as e:
        console.print(f"[red]Error: Failed to import sla.py: {e}[/red]")
        console.print("[yellow]Please ensure sla.py exists in the project root[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error executing sla.py: {str(e)}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
