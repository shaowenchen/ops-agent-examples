# -*- coding: utf-8 -*-
"""
Main entry point for Ops Agent
"""

import os
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from ops_agent.config import ConfigLoader
from ops_agent.core.agent import ReActAgent
from ops_agent.utils.logging import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


def print_banner():
    """
    Print application banner
    """
    banner = """
    ===============================================================
    
            Ops Agent - LangChain Edition
    
            Intelligent Operations Automation Platform
    
    ===============================================================
    """
    console.print(banner, style="bold cyan")


@click.command()
@click.argument('task_file', type=click.Path(exists=True))
@click.option("-c", "--config", default=None, help="Path to configuration file")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging")
@click.option("--max-steps", default=10, help="Maximum number of ReAct steps")
@click.option("--step-timeout", default=30.0, help="Timeout for each step in seconds")
def run(task_file, config, verbose, max_steps, step_timeout):
    """Run tasks from a configuration file"""
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)

    print_banner()
    
    try:
        # Initialize components
        console.print("\n[cyan]Initializing Enhanced ReAct Agent...[/cyan]")
        
        config_loader = ConfigLoader(config_file=config)
        agent = ReActAgent(
            config_loader, 
            verbose=verbose,
            max_steps=max_steps,
            step_timeout=step_timeout
        )
        
        # Load tasks
        console.print(f"\n[cyan]Loading tasks from: {task_file}[/cyan]")
        tasks_config = config_loader.load_tasks(task_file)
        
        console.print(f"[green]Found {len(tasks_config.tasks)} task(s) to execute[/green]\n")
        
        # Execute tasks
        results = agent.execute_tasks(tasks_config.tasks)
        
        # Print results with beautiful Markdown summaries
        console.print("\n")
        console.print("=" * 80, style="bold cyan")
        console.print(" " * 25 + "📊 TASK EXECUTION RESULTS", style="bold cyan")
        console.print("=" * 80, style="bold cyan")
        console.print()
        
        for idx, result in enumerate(results, 1):
            status_style = "green" if result["status"] == "success" else "red"
            task_name = result.get('task_name', result.get('name', 'unknown'))
            
            # Show summary in Markdown format if available
            result_data = result.get('result', {})
            if isinstance(result_data, dict):
                summary = result_data.get('summary')
                total_steps = result_data.get('total_steps', 0)
                successful_steps = result_data.get('successful_steps', 0)
                failed_steps = result_data.get('failed_steps', 0)
                total_time = result_data.get('total_execution_time', 0)
                steps = result_data.get('steps', [])
                
                if summary:
                    # Render Markdown summary
                    subtitle = f"[{status_style}]Status: {result['status'].upper()}[/{status_style}]"
                    if total_steps:
                        subtitle += f" | ReAct Steps: {total_steps}"
                        if successful_steps or failed_steps:
                            subtitle += f" (✅{successful_steps} ❌{failed_steps})"
                        if total_time:
                            subtitle += f" | Time: {total_time:.1f}s"
                    
                    console.print()
                    console.print(Panel(
                        Markdown(summary),
                        title=f"[bold]Task {idx}: {task_name}[/bold]",
                        subtitle=subtitle,
                        border_style="cyan",
                        padding=(1, 2)
                    ))
                    
                    # Show ReAct steps if available
                    if steps:
                        console.print("\n[bold cyan]🔄 ReAct Steps:[/bold cyan]")
                        for step in steps:
                            status_icon = "✅" if step.status.value == "completed" else "❌" if step.status.value == "failed" else "⏳"
                            console.print(f"  {status_icon} [dim]Step {step.step_number}:[/dim] {step.thought[:100]}...")
                            if step.action:
                                console.print(f"    [yellow]Action:[/yellow] {step.action}")
                            if step.observation:
                                console.print(f"    [blue]Observation:[/blue] {step.observation[:100]}...")
                            if step.error:
                                console.print(f"    [red]Error:[/red] {step.error[:100]}...")
                            if step.execution_time:
                                console.print(f"    [dim]Time: {step.execution_time:.2f}s[/dim]")
                else:
                    # Fallback if no summary
                    console.print(f"\n[bold]Task {idx}: {task_name}[/bold]")
                    console.print(f"Status: [{status_style}]{result['status']}[/{status_style}]")
                    if total_steps:
                        console.print(f"ReAct Steps: {total_steps}")
                        if successful_steps or failed_steps:
                            console.print(f"Successful: {successful_steps}, Failed: {failed_steps}")
                        if total_time:
                            console.print(f"Total Time: {total_time:.2f}s")
            else:
                # Simple format for non-dict results
                console.print(f"\n[bold]Task {idx}: {task_name}[/bold]")
                console.print(f"Status: [{status_style}]{result['status']}[/{status_style}]")
        
        # Overall Summary
        success_count = sum(1 for r in results if r["status"] == "success")
        failed_count = len(results) - success_count
        
        console.print()
        console.print("=" * 80, style="bold cyan")
        console.print(" " * 30 + "📈 OVERALL SUMMARY", style="bold cyan")
        console.print("=" * 80, style="bold cyan")
        console.print()
        console.print(f"  ✅ Successful Tasks: [bold green]{success_count}[/bold green]")
        console.print(f"  ❌ Failed Tasks:     [bold red]{failed_count}[/bold red]")
        console.print(f"  📊 Total Tasks:      [bold]{len(results)}[/bold]")
        console.print()
        console.print("=" * 80, style="bold cyan")
        console.print()
        
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]\n", style="bold")
        logger.exception("Error running tasks")
        sys.exit(1)


def main():
    """Main entry point"""
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    run()


if __name__ == "__main__":
    main()