#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for Ops Agent SLO
Executes run.py which contains direct module composition code
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
    """Main entry point - executes run.py"""
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
    console.print("\n[cyan]Executing run.py...[/cyan]\n")
    
    # Import and execute run.py
    try:
        from run import main as run_main
        run_main()
    except ImportError as e:
        console.print(f"[red]Error: Failed to import run.py: {e}[/red]")
        console.print("[yellow]Please ensure run.py exists in the project root[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error executing run.py: {str(e)}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
