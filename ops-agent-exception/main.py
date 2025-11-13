# -*- coding: utf-8 -*-
"""
异常分析框架主入口
"""

import os
import sys
import json
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ops_agent.config import ConfigLoader
from ops_agent.core import AnomalyAnalyzer, AlarmEvent
from ops_agent.utils.logging import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


def print_banner():
    """打印应用横幅"""
    banner = """
    ===============================================================
    
            Ops Agent Exception - 异常分析框架
    
            智能异常分析与定位平台
    
    ===============================================================
    """
    console.print(banner, style="bold cyan")


def parse_text_alarm(file_path: str) -> dict:
    """
    解析文本格式的告警文件（简单处理，仅识别为文本格式）
    
    Args:
        file_path: 文件路径
        
    Returns:
        告警数据字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 简单处理文本格式，生成基本的告警数据
    import hashlib
    file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
    
    alarm_data = {
        'event_id': f"text-alarm-{file_hash}",
        'timestamp': '',  # TODO: 从文本中提取时间
        'source': 'text',
        'severity': 'high',
        'message': content[:200] if len(content) > 200 else content,  # 使用前200字符作为消息
        'metadata': {
            'raw_content': content,  # 保存原始文本内容
            'file_path': file_path
        }
    }
    
    return alarm_data


@click.command()
@click.argument('alarm_file', required=False, default='input.txt', type=click.Path())
@click.option("-c", "--config", default=None, help="配置文件路径")
@click.option("--verbose", is_flag=True, default=False, help="启用详细日志")
def run(alarm_file, config, verbose):
    """
    运行异常分析
    
    ALARM_FILE: 告警事件文件路径（默认: input.txt，支持 JSON 或文本格式）
    """
    # 设置日志
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    
    print_banner()
    
    try:
        # 初始化组件
        console.print("\n[cyan]初始化异常分析引擎...[/cyan]")
        
        config_loader = ConfigLoader(config_file=config)
        analyzer = AnomalyAnalyzer(config_loader)
        
        # 检查文件是否存在
        if not os.path.exists(alarm_file):
            console.print(f"\n[red]错误: 文件不存在: {alarm_file}[/red]")
            console.print(f"[yellow]提示: 请确保文件存在，或使用默认的 input.txt[/yellow]\n")
            sys.exit(1)
        
        # 加载告警事件
        console.print(f"\n[cyan]加载告警事件: {alarm_file}[/cyan]")
        
        # 判断文件格式并解析
        try:
            # 尝试作为 JSON 解析
            with open(alarm_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('{'):
                    alarm_data = json.loads(content)
                else:
                    # 作为文本格式解析
                    alarm_data = parse_text_alarm(alarm_file)
        except json.JSONDecodeError:
            # JSON 解析失败，尝试文本格式
            alarm_data = parse_text_alarm(alarm_file)
        except Exception as e:
            console.print(f"\n[red]错误: 无法解析告警文件: {str(e)}[/red]\n")
            sys.exit(1)
        
        # 创建告警事件对象
        alarm_event = AlarmEvent(
            event_id=alarm_data.get('event_id', ''),
            timestamp=alarm_data.get('timestamp', ''),
            source=alarm_data.get('source', ''),
            severity=alarm_data.get('severity', ''),
            message=alarm_data.get('message', ''),
            metadata=alarm_data.get('metadata', {})
        )
        
        console.print(f"[green]告警事件ID: {alarm_event.event_id}[/green]")
        console.print(f"[green]告警来源: {alarm_event.source}[/green]")
        console.print(f"[green]严重程度: {alarm_event.severity}[/green]\n")
        
        # 执行异常分析
        console.print("[cyan]开始执行异常分析流程...[/cyan]\n")
        discovered_points = analyzer.analyze(alarm_event)
        
        # 显示结果
        console.print("\n")
        console.print("=" * 80, style="bold cyan")
        console.print(" " * 25 + "📊 异常分析结果", style="bold cyan")
        console.print("=" * 80, style="bold cyan")
        console.print()
        
        if discovered_points:
            # 创建结果表格
            table = Table(title="发现的异常点")
            table.add_column("实体ID", style="cyan")
            table.add_column("实体类型", style="magenta")
            table.add_column("实体名称", style="green")
            table.add_column("置信度", style="yellow")
            table.add_column("异常类型", style="blue")
            
            for point in discovered_points:
                table.add_row(
                    point.entity_id,
                    point.entity_type,
                    point.entity_name,
                    f"{point.confidence:.2%}",
                    point.anomaly_type
                )
            
            console.print(table)
            console.print()
            
            # 显示详细信息
            for idx, point in enumerate(discovered_points, 1):
                console.print(Panel(
                    f"""
[bold]实体信息:[/bold]
  ID: {point.entity_id}
  类型: {point.entity_type}
  名称: {point.entity_name}

[bold]异常信息:[/bold]
  置信度: {point.confidence:.2%}
  异常类型: {point.anomaly_type}
  时间: {point.timestamp}

[bold]异常指标:[/bold]
{chr(10).join(f'  - {indicator}' for indicator in point.indicators[:5])}

[bold]推荐建议:[/bold]
{chr(10).join(f'  {i+1}. {rec}' for i, rec in enumerate(point.recommendations[:3]))}
                    """.strip(),
                    title=f"[bold]异常点 {idx}[/bold]",
                    border_style="cyan",
                    padding=(1, 2)
                ))
                console.print()
        else:
            console.print("[yellow]未发现异常点[/yellow]\n")
        
        # 总体统计
        console.print("=" * 80, style="bold cyan")
        console.print(" " * 30 + "📈 统计信息", style="bold cyan")
        console.print("=" * 80, style="bold cyan")
        console.print()
        console.print(f"  📊 发现的异常点数量: [bold green]{len(discovered_points)}[/bold green]")
        console.print()
        console.print("=" * 80, style="bold cyan")
        console.print()
        
    except Exception as e:
        console.print(f"\n[red]错误: {str(e)}[/red]\n", style="bold")
        logger.exception("执行异常分析失败")
        sys.exit(1)


def main():
    """主入口"""
    # 加载 .env 文件
    from dotenv import load_dotenv
    load_dotenv()
    
    run()


if __name__ == "__main__":
    main()

