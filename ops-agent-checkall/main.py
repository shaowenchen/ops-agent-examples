#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for Ops Agent CheckAll
Executes a series of MCP queries
"""

import os
import sys
import json
import click
from typing import Any
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_agent.config import ConfigLoader
from ops_agent.core import MCPQueryExecutor
from ops_agent.core.formatters import format_query_result
from ops_agent.utils.logging import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


def print_banner():
    """Print application banner"""
    banner = """
    ===============================================================
    
            Ops Agent CheckAll
    
            MCP Query Executor
    
    ===============================================================
    """
    console.print(banner, style="bold cyan")


@click.command()
@click.option("-c", "--config", default=None, help="Path to configuration file")
@click.option("-q", "--queries", default=None, help="Path to queries YAML file")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging")
def run(config, queries, verbose):
    """Execute MCP queries"""
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    
    print_banner()
    
    try:
        # Initialize configuration
        console.print("\n[cyan]Loading configuration...[/cyan]")
        
        # Debug: Show environment variables (mask sensitive info)
        import os
        mcp_url = os.environ.get('MCP_SERVERURL') or os.environ.get('MCP_SERVER_URL')
        if mcp_url:
            console.print(f"[dim]Found MCP_SERVERURL from environment: {mcp_url[:50]}...[/dim]")
        mcp_token = os.environ.get('MCP_TOKEN') or os.environ.get('MCP_AUTH_TOKEN')
        if mcp_token:
            console.print(f"[dim]Found MCP_TOKEN from environment: {'*' * min(len(mcp_token), 20)}...[/dim]")
        
        config_loader = ConfigLoader(config_file=config)
        config_loader.load_config()
        
        # Show loaded configuration (mask sensitive info)
        mcp_config = config_loader.mcp_config
        console.print(f"[dim]Loaded MCP server URL: {mcp_config.server_url[:50] if mcp_config.server_url else 'Not set'}...[/dim]")
        console.print(f"[dim]Loaded MCP token: {'*' * min(len(mcp_config.token), 20) if mcp_config.token else 'Not set'}...[/dim]")
        
        # Load queries from YAML file
        if queries:
            queries_file = queries
        else:
            # Try default locations
            default_locations = [
                os.path.join(os.path.dirname(__file__), "default.yaml"),
                "./default.yaml",
            ]
            queries_file = None
            for loc in default_locations:
                if os.path.exists(loc):
                    queries_file = loc
                    break
            
            if not queries_file:
                console.print("[red]Error: No queries file found. Please specify with -q/--queries[/red]")
                sys.exit(1)
        
        console.print(f"[cyan]Loading queries from: {queries_file}[/cyan]")
        import yaml
        with open(queries_file, 'r', encoding='utf-8') as f:
            queries_config = yaml.safe_load(f)
        
        query_list = queries_config.get('queries', [])
        
        if not query_list:
            console.print("[red]Error: No queries found in queries file[/red]")
            sys.exit(1)
        
        console.print(f"[green]Found {len(query_list)} query(ies) to execute[/green]\n")
        
        # Initialize components
        console.print("[cyan]Initializing MCP Query Executor...[/cyan]")
        query_executor = MCPQueryExecutor(config_loader)
        
        # List all available MCP tools (simplified output)
        console.print("\n[cyan]Fetching available MCP tools...[/cyan]")
        try:
            available_tools = query_executor.list_available_tools()
            
            if available_tools:
                console.print(f"[green]Found {len(available_tools)} available tool(s)[/green]")
                
                # Simple list format
                tool_names = [tool.get('name', 'unknown') for tool in available_tools]
                console.print(f"[dim]{', '.join(tool_names)}[/dim]")
            else:
                console.print("[yellow]No tools found or failed to list tools[/yellow]")
        except Exception as e:
            console.print(f"[red]Failed to list available tools: {str(e)}[/red]")
            logger.exception("Error listing tools")
        
        # Debug: Show queries that will be executed
        if verbose:
            console.print(f"\n[dim]Queries to execute:[/dim]")
            for idx, query in enumerate(query_list, 1):
                tool_name = query.get('tool_name', 'unknown')
                args = query.get('args', {})
                console.print(f"  [dim]{idx}. {tool_name} with args: {json.dumps(args, ensure_ascii=False)}[/dim]")
        
        # Execute queries
        console.print("\n[cyan]Executing MCP queries...[/cyan]")
        console.print("=" * 80)
        
        results = query_executor.execute_queries(query_list)
        
        # Format all query results and build output
        console.print("\n")
        console.print("=" * 80, style="bold cyan")
        console.print(" " * 25 + "📊 QUERY RESULTS", style="bold cyan")
        console.print("=" * 80, style="bold cyan")
        console.print()
        
        # Build formatted output from all queries
        output_lines = []
        for result in results:
            if result.get('success', False):
                tool_name = result.get('tool_name', 'unknown')
                desc = result.get('desc', '')
                result_data = result.get('result', {})
                
                # Print raw query result first
                console.print(f"[cyan]Query: {tool_name}[/cyan]")
                if desc:
                    console.print(f"[dim]Description: {desc}[/dim]")
                console.print(f"[dim]Raw result:[/dim]")
                if result_data:
                    # Print raw result structure
                    raw_output = json.dumps(result_data, ensure_ascii=False, indent=2)
                    # Limit output length for readability
                    if len(raw_output) > 2000:
                        console.print(f"[dim]{raw_output[:2000]}...[/dim]")
                        console.print(f"[dim](Truncated, full result in logs)[/dim]")
                    else:
                        console.print(f"[dim]{raw_output}[/dim]")
                else:
                    console.print(f"[yellow]No data returned[/yellow]")
                console.print()
                
                # Check if we have actual data
                has_data = False
                if result_data:
                    # Check if content exists and has data
                    if isinstance(result_data, dict):
                        if 'content' in result_data:
                            content = result_data['content']
                            if isinstance(content, list) and len(content) > 0:
                                has_data = True
                            elif isinstance(content, str) and content.strip():
                                has_data = True
                            elif content:  # Other truthy values
                                has_data = True
                        elif result_data:  # Has other keys
                            has_data = True
                    elif result_data:  # Not empty
                        has_data = True
                
                # Debug: log the structure for troubleshooting
                if verbose:
                    logger.debug(f"Processing result for {tool_name}: {json.dumps(result_data, ensure_ascii=False)[:500]}")
                
                # Get formater from result or use tool_name as fallback
                formater_name = result.get('formater')
                formatted_result = format_query_result(result_data, formatter_name=formater_name, tool_name=tool_name)
                
                # 总是输出 desc，即使结果为空
                if desc:
                    output_lines.append(f"### {desc}")
                    output_lines.append("")
                
                # 如果有格式化结果，输出结果
                if formatted_result and formatted_result.strip():
                    output_lines.append(formatted_result)
                    output_lines.append("")
                else:
                    # 即使没有数据，也保留空行以保持格式
                    output_lines.append("")
        
        # Combine all formatted results into output
        output = "\n".join(output_lines).strip()
        
        # Display output
        if output:
            console.print(output)
        else:
            console.print("[yellow]No data to display. All queries may have returned empty results.[/yellow]")
            if verbose:
                console.print("[dim]Use --verbose to see detailed query results[/dim]")
        
        # Save results to file
        output_file = "results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            output_data = {
                "queries": results,
                "output": output
            }
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"\n[green]Results saved to: {output_file}[/green]")
        
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]\n", style="bold")
        logger.exception("Error running queries")
        sys.exit(1)


def main():
    """Main entry point"""
    # Load .env file if available (must be done before any config loading)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Also try to load from .env file in current directory and project root
    import os
    env_files = [
        os.path.join(os.path.dirname(__file__), '.env'),
        '.env',
        os.path.expanduser('~/.env')
    ]
    for env_file in env_files:
        if os.path.exists(env_file):
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file, override=False)  # Don't override existing env vars
            except:
                pass
            break
    
    run()


if __name__ == "__main__":
    main()

