"""
Formatter module for formatting query results based on different formatter types.
"""
import json
import re
from typing import Any, Dict, List
from collections import Counter
from abc import ABC, abstractmethod

from ops_agent.utils.logging import get_logger

logger = get_logger(__name__)


class BaseFormatter(ABC):
    """Base formatter class for all formatters"""
    
    @abstractmethod
    def format(self, result_data: Any) -> str:
        """
        Format query result data
        
        Args:
            result_data: Query result data
            
        Returns:
            Formatted string
        """
        pass
    
    def _extract_content(self, result_data: Any) -> Any:
        """
        Extract content from MCP result format
        
        Args:
            result_data: Raw result data
            
        Returns:
            Extracted content
        """
        content = None
        if isinstance(result_data, dict):
            if 'content' in result_data:
                content = result_data['content']
                # If content is a string, try to parse it as JSON
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except:
                        # If parsing fails, might be a plain string or already formatted
                        pass
            else:
                # Try to find data in other common keys
                if 'data' in result_data:
                    content = result_data['data']
                elif 'result' in result_data:
                    content = result_data['result']
                else:
                    content = result_data
        elif isinstance(result_data, list):
            content = result_data
        else:
            content = result_data
        
        return content


class MetricsFormatter(BaseFormatter):
    """Formatter for Prometheus metrics query results"""
    
    def format(self, result_data: Any) -> str:
        """
        Format metrics query result - only show object and value
        Parse Prometheus query result format
        """
        formatted_lines = []
        content = self._extract_content(result_data)
        
        # Handle Prometheus response format: {"status":"success","data":{"resultType":"vector","result":[...]}}
        if isinstance(content, dict):
            if 'status' in content and 'data' in content:
                # Prometheus API response format
                data = content.get('data', {})
                if isinstance(data, dict) and 'result' in data:
                    content = data['result']
            elif 'data' in content:
                data = content['data']
                if isinstance(data, dict) and 'result' in data:
                    content = data['result']
        
        # Handle list of items (Prometheus result array)
        if isinstance(content, list):
            # First, try to parse if content is a list of JSON strings
            parsed_items = []
            for item in content:
                if isinstance(item, str):
                    try:
                        # Try to parse the string as JSON
                        parsed = json.loads(item)
                        # If it's a Prometheus response format, extract the result array
                        if isinstance(parsed, dict) and 'status' in parsed and 'data' in parsed:
                            data = parsed.get('data', {})
                            if isinstance(data, dict) and 'result' in data:
                                # This is a Prometheus API response, extract the result array
                                parsed_items.extend(data['result'] if isinstance(data['result'], list) else [data['result']])
                            else:
                                parsed_items.append(parsed)
                        elif isinstance(parsed, dict) and 'data' in parsed:
                            # Nested data structure
                            data = parsed.get('data', {})
                            if isinstance(data, dict) and 'result' in data:
                                parsed_items.extend(data['result'] if isinstance(data['result'], list) else [data['result']])
                            else:
                                parsed_items.append(parsed)
                        else:
                            parsed_items.append(parsed)
                    except:
                        # If parsing fails, skip this item
                        continue
                else:
                    parsed_items.append(item)
            
            # Now process the parsed items and output each result on a separate line
            for item in parsed_items:
                if isinstance(item, dict):
                    # Extract metric labels and value
                    metric = item.get('metric', {})
                    value = item.get('value')
                    
                    if isinstance(metric, dict) and value:
                        # Extract all labels, excluding internal Prometheus labels
                        # Priority order: request_uri, code, then other labels (excluding __name__, job, etc.)
                        internal_labels = {'__name__', 'job', 'instance', 'prometheus', 'replica'}
                        node_labels = {'node', 'instance', 'host', 'hostname'}
                        
                        # Priority labels to show first
                        priority_labels = ['request_uri', 'code', 'destination_app', 'destination_workload_namespace']
                        
                        # Collect all label values in priority order
                        label_values = []
                        label_keys_used = set()
                        
                        # First, add priority labels
                        for label_key in priority_labels:
                            if label_key in metric and label_key not in internal_labels:
                                label_values.append(metric[label_key])
                                label_keys_used.add(label_key)
                        
                        # Then, add other non-internal, non-node labels
                        for label_key, label_value in metric.items():
                            if (label_key not in internal_labels and 
                                label_key not in node_labels and 
                                label_key not in label_keys_used):
                                label_values.append(label_value)
                                label_keys_used.add(label_key)
                        
                        # Finally, add node labels if no other labels found
                        if not label_values:
                            for node_key in node_labels:
                                if node_key in metric:
                                    label_values.append(metric[node_key])
                                    break
                        
                        # If still no labels, use first available label
                        if not label_values and metric:
                            for key, val in metric.items():
                                if key not in internal_labels:
                                    label_values.append(val)
                                    break
                        
                        # Extract actual value, skip timestamp if it's in array format [timestamp, value]
                        if isinstance(value, list) and len(value) >= 2:
                            actual_value = value[1]
                        else:
                            actual_value = value
                        
                        # Convert to integer if it's a number
                        if isinstance(actual_value, (int, float)):
                            actual_value = int(actual_value)
                        elif isinstance(actual_value, str):
                            # Try to extract number from string
                            numbers = re.findall(r'-?\d+\.?\d*', actual_value)
                            if numbers:
                                try:
                                    actual_value = int(float(numbers[-1]))
                                except:
                                    continue
                            else:
                                continue
                        
                        # Format as "- label1, label2: value" on separate line
                        if label_values:
                            labels_str = ", ".join(str(v) for v in label_values)
                            formatted_lines.append(f"- {labels_str}: {actual_value}")
                        else:
                            formatted_lines.append(f"- {actual_value}")
                    else:
                        # Fallback: try to extract value from item
                        if 'value' in item:
                            fallback_value = item['value']
                            if isinstance(fallback_value, list) and len(fallback_value) >= 2:
                                fallback_value = fallback_value[1]
                            
                            if isinstance(fallback_value, (int, float)):
                                formatted_lines.append(f"- {int(fallback_value)}")
                            elif isinstance(fallback_value, str):
                                numbers = re.findall(r'-?\d+\.?\d*', fallback_value)
                                if numbers:
                                    try:
                                        formatted_lines.append(f"- {int(float(numbers[-1]))}")
                                    except:
                                        pass
                elif item:
                    # Try to convert to integer if it's a number
                    if isinstance(item, (int, float)):
                        formatted_lines.append(f"- {int(item)}")
                    else:
                        formatted_lines.append(f"- {str(item)[:200]}")
        elif isinstance(content, dict):
            # Single metric result
            if 'metric' in content and 'value' in content:
                metric = content.get('metric', {})
                value = content.get('value')
                
                if isinstance(metric, dict):
                    # Extract all labels, excluding internal Prometheus labels
                    internal_labels = {'__name__', 'job', 'instance', 'prometheus', 'replica'}
                    node_labels = {'node', 'instance', 'host', 'hostname'}
                    
                    # Priority labels to show first
                    priority_labels = ['request_uri', 'code', 'destination_app', 'destination_workload_namespace']
                    
                    # Collect all label values in priority order
                    label_values = []
                    label_keys_used = set()
                    
                    # First, add priority labels
                    for label_key in priority_labels:
                        if label_key in metric and label_key not in internal_labels:
                            label_values.append(metric[label_key])
                            label_keys_used.add(label_key)
                    
                    # Then, add other non-internal, non-node labels
                    for label_key, label_value in metric.items():
                        if (label_key not in internal_labels and 
                            label_key not in node_labels and 
                            label_key not in label_keys_used):
                            label_values.append(label_value)
                            label_keys_used.add(label_key)
                    
                    # Finally, add node labels if no other labels found
                    if not label_values:
                        for node_key in node_labels:
                            if node_key in metric:
                                label_values.append(metric[node_key])
                                break
                    
                    # If still no labels, use first available label
                    if not label_values and metric:
                        for key, val in metric.items():
                            if key not in internal_labels:
                                label_values.append(val)
                                break
                    
                    # Extract actual value, skip timestamp if it's in array format [timestamp, value]
                    if isinstance(value, list) and len(value) >= 2:
                        actual_value = value[1]
                    else:
                        actual_value = value
                    
                    # Convert to integer if it's a number
                    if isinstance(actual_value, (int, float)):
                        actual_value = int(actual_value)
                    
                    # Format as "- label1, label2: value"
                    if label_values:
                        labels_str = ", ".join(str(v) for v in label_values)
                        formatted_lines.append(f"- {labels_str}: {actual_value}")
                    else:
                        formatted_lines.append(f"- {actual_value}")
            else:
                # Try to format as JSON
                content_str = json.dumps(content, ensure_ascii=False, indent=2)
                if len(content_str) < 500:
                    return content_str
                else:
                    return content_str[:500] + "..."
        elif content:
            return str(content)
        
        return "\n".join(formatted_lines) if formatted_lines else ""


class AtmsLogsFormatter(BaseFormatter):
    """Formatter for ATMS application logs query results"""
    
    def format(self, result_data: Any) -> str:
        """
        Format ATMS logs query result - show aggregation statistics
        For aggregation queries, only show key and doc_count
        """
        formatted_lines = []
        content = self._extract_content(result_data)
        
        # If content is a list of strings (common MCP format), try to parse each string
        if isinstance(content, list):
            parsed_items = []
            for item in content:
                if isinstance(item, str):
                    try:
                        parsed = json.loads(item)
                        parsed_items.append(parsed)
                    except:
                        parsed_items.append(item)
                else:
                    parsed_items.append(item)
            # Try to find aggregations in any of the parsed items
            found_aggregations = False
            for item in parsed_items:
                if isinstance(item, dict):
                    # Check if this item has aggregations
                    if 'aggregations' in item:
                        content = item
                        found_aggregations = True
                        break
                    # Or check nested structures
                    for key in ['hits', 'data', 'result']:
                        if key in item and isinstance(item[key], dict) and 'aggregations' in item[key]:
                            content = item[key]
                            found_aggregations = True
                            break
                    if found_aggregations:
                        break
            # If we didn't find aggregations, use the first parsed item or original list
            if not found_aggregations:
                content = parsed_items[0] if len(parsed_items) == 1 else parsed_items
        
        # If content is still a string after parsing attempt, try to parse it
        if isinstance(content, str) and content.strip():
            try:
                content = json.loads(content)
            except:
                return content
        
        # Check if this is an Elasticsearch aggregation result
        def extract_aggregations(data):
            """Recursively extract aggregations from Elasticsearch response"""
            if isinstance(data, dict):
                if 'aggregations' in data:
                    return data['aggregations']
                # Check nested structures
                for key in ['hits', 'data', 'result']:
                    if key in data:
                        result = extract_aggregations(data[key])
                        if result:
                            return result
            elif isinstance(data, list):
                for item in data:
                    result = extract_aggregations(item)
                    if result:
                        return result
            return None
        
        aggregations = extract_aggregations(content)
        
        # If we found aggregations, format them
        if aggregations:
            for agg_name, agg_data in aggregations.items():
                if isinstance(agg_data, dict) and 'buckets' in agg_data:
                    buckets = agg_data['buckets']
                    
                    # Only show first 5 results
                    for bucket in buckets[:5]:
                        if isinstance(bucket, dict) and 'doc_count' in bucket:
                            # Extract key - could be 'key', 'key_as_string', or other variations
                            bucket_key = None
                            if 'key' in bucket:
                                bucket_key = bucket['key']
                            elif 'key_as_string' in bucket:
                                bucket_key = bucket['key_as_string']
                            elif len(bucket) == 2 and 'doc_count' in bucket:
                                # If only two fields and one is doc_count, the other is likely the key
                                for k, v in bucket.items():
                                    if k != 'doc_count':
                                        bucket_key = v
                                        break
                            
                            if bucket_key is not None:
                                error_count = bucket['doc_count']
                                # Format as friendly output: 节点名称: 错误数量
                                formatted_lines.append(f"  - {bucket_key}: {error_count}")
        
        if formatted_lines:
            return "\n".join(formatted_lines)
        else:
            # No aggregation buckets found, return empty
            return ""


class IngressLogsFormatter(BaseFormatter):
    """Formatter for Ingress gateway logs query results"""
    
    def format(self, result_data: Any) -> str:
        """
        Format Ingress logs query result - show detailed log entries with key fields
        """
        formatted_lines = []
        content = self._extract_content(result_data)
        
        # If content is a list of strings (common MCP format), try to parse each string
        if isinstance(content, list):
            parsed_items = []
            for item in content:
                if isinstance(item, str):
                    try:
                        parsed = json.loads(item)
                        parsed_items.append(parsed)
                    except:
                        parsed_items.append(item)
                else:
                    parsed_items.append(item)
            content = parsed_items[0] if len(parsed_items) == 1 else parsed_items
        
        # If content is still a string after parsing attempt, try to parse it
        if isinstance(content, str) and content.strip():
            try:
                content = json.loads(content)
            except:
                return content
        
        # Extract hits from Elasticsearch response
        def extract_hits(data):
            """Recursively extract hits from Elasticsearch response"""
            if isinstance(data, dict):
                if 'hits' in data:
                    hits = data['hits']
                    if isinstance(hits, dict) and 'hits' in hits:
                        return hits['hits']
                    elif isinstance(hits, list):
                        return hits
                # Check nested structures
                for key in ['data', 'result']:
                    if key in data:
                        result = extract_hits(data[key])
                        if result:
                            return result
            elif isinstance(data, list):
                for item in data:
                    result = extract_hits(item)
                    if result:
                        return result
            return None
        
        hits = extract_hits(content)
        
        # Statistics counter for nodes
        node_counter = Counter()
        
        # If we found hits, count errors by node (don't output detailed entries)
        if hits:
            for hit in hits:
                if isinstance(hit, dict):
                    source = hit.get('_source', hit)
                    # Extract node field
                    node = source.get('k8s', {}).get('node', source.get('node', '-'))
                    
                    # Count errors by node
                    if node != '-':
                        node_counter[node] += 1
        else:
            # Fallback: try to extract node from general log entries
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        # Try to extract node and count
                        node = item.get('k8s', {}).get('node', item.get('node', '-'))
                        if node != '-':
                            node_counter[node] += 1
            elif isinstance(content, dict):
                node = content.get('k8s', {}).get('node', content.get('node', '-'))
                if node != '-':
                    node_counter[node] += 1
        
        # Output only node error statistics (only first 5)
        if node_counter:
            for node, count in node_counter.most_common(5):
                formatted_lines.append(f"  - {node}: {count}")
        
        return "\n".join(formatted_lines) if formatted_lines else ""


class GeneralLogsFormatter(BaseFormatter):
    """General formatter for logs query results (fallback)"""
    
    def format(self, result_data: Any) -> str:
        """
        Format logs query result - show cluster, namespace, pod, message and statistics
        """
        formatted_lines = []
        log_entries = []
        content = self._extract_content(result_data)
        
        # If content is a list of strings (common MCP format), try to parse each string
        if isinstance(content, list):
            parsed_items = []
            for item in content:
                if isinstance(item, str):
                    try:
                        parsed = json.loads(item)
                        parsed_items.append(parsed)
                    except:
                        parsed_items.append(item)
            content = parsed_items[0] if len(parsed_items) == 1 else parsed_items
        
        # If content is still a string after parsing attempt, try to parse it
        if isinstance(content, str) and content.strip():
            try:
                content = json.loads(content)
            except:
                return content
        
        # Statistics counters
        cluster_counter = Counter()
        node_counter = Counter()
        app_counter = Counter()  # namespace + pod combination
        
        # Handle list of log entries
        if isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    try:
                        item = json.loads(item)
                    except:
                        formatted_lines.append(f"- {item}")
                        continue
                
                if isinstance(item, dict):
                    # Extract fields - try multiple possible paths
                    kubernetes = item.get('kubernetes', {})
                    metadata = item.get('@metadata', {})
                    
                    cluster = (item.get('cluster') or 
                              kubernetes.get('cluster_name') or 
                              metadata.get('cluster') or 
                              item.get('fields', {}).get('cluster') or
                              '-')
                    
                    namespace = (kubernetes.get('namespace_name') or 
                               kubernetes.get('namespace') or
                               item.get('namespace') or 
                               metadata.get('namespace') or
                               item.get('fields', {}).get('namespace') or
                               '-')
                    
                    pod = (kubernetes.get('pod_name') or 
                          kubernetes.get('pod') or
                          item.get('pod') or 
                          metadata.get('pod') or
                          item.get('fields', {}).get('pod') or
                          '-')
                    
                    node = (kubernetes.get('host') or
                           kubernetes.get('node') or
                           item.get('node') or 
                           metadata.get('node') or
                           item.get('fields', {}).get('node') or
                           '-')
                    
                    message = (item.get('message') or 
                              item.get('log') or 
                              item.get('msg') or
                              item.get('_source', {}).get('message') or
                              item.get('_source', {}).get('log') or
                              str(item)[:200])  # Fallback to string representation
                    
                    # Store entry for output
                    log_entries.append({
                        'cluster': cluster,
                        'namespace': namespace,
                        'pod': pod,
                        'node': node,
                        'message': message
                    })
                    
                    # Update statistics
                    if cluster != '-':
                        cluster_counter[cluster] += 1
                    if node != '-':
                        node_counter[node] += 1
                    if namespace != '-' and pod != '-':
                        app_key = f"{namespace}/{pod}"
                        app_counter[app_key] += 1
        elif isinstance(content, dict):
            # Single log entry
            kubernetes = content.get('kubernetes', {})
            metadata = content.get('@metadata', {})
            
            cluster = (content.get('cluster') or 
                      kubernetes.get('cluster_name') or 
                      metadata.get('cluster') or 
                      content.get('fields', {}).get('cluster') or
                      '-')
            
            namespace = (kubernetes.get('namespace_name') or 
                       kubernetes.get('namespace') or
                       content.get('namespace') or 
                       metadata.get('namespace') or
                       content.get('fields', {}).get('namespace') or
                       '-')
            
            pod = (kubernetes.get('pod_name') or 
                  kubernetes.get('pod') or
                  content.get('pod') or 
                  metadata.get('pod') or
                  content.get('fields', {}).get('pod') or
                  '-')
            
            node = (kubernetes.get('host') or
                   kubernetes.get('node') or
                   content.get('node') or 
                   metadata.get('node') or
                   content.get('fields', {}).get('node') or
                   '-')
            
            message = (content.get('message') or 
                      content.get('log') or 
                      content.get('msg') or
                      content.get('_source', {}).get('message') or
                      content.get('_source', {}).get('log') or
                      str(content)[:200])
            
            log_entries.append({
                'cluster': cluster,
                'namespace': namespace,
                'pod': pod,
                'node': node,
                'message': message
            })
            
            if cluster != '-':
                cluster_counter[cluster] += 1
            if node != '-':
                node_counter[node] += 1
            if namespace != '-' and pod != '-':
                app_key = f"{namespace}/{pod}"
                app_counter[app_key] += 1
        
        # Output log entries
        if log_entries:
            for entry in log_entries:
                formatted_lines.append(f"Cluster: {entry['cluster']}, Namespace: {entry['namespace']}, Pod: {entry['pod']}")
                formatted_lines.append(f"  Message: {entry['message']}")
                formatted_lines.append("")
        
        # Output statistics
        if cluster_counter or node_counter or app_counter:
            formatted_lines.append("=== 异常统计 ===")
            formatted_lines.append("")
            
            # Top clusters
            if cluster_counter:
                formatted_lines.append("异常最多的集群:")
                for cluster, count in cluster_counter.most_common(10):
                    formatted_lines.append(f"  - {cluster}: {count} 条异常")
                formatted_lines.append("")
            
            # Top nodes
            if node_counter:
                formatted_lines.append("异常最多的节点:")
                for node, count in node_counter.most_common(10):
                    formatted_lines.append(f"  - {node}: {count} 条异常")
                formatted_lines.append("")
            
            # Top apps
            if app_counter:
                formatted_lines.append("异常最多的应用:")
                for app, count in app_counter.most_common(10):
                    formatted_lines.append(f"  - {app}: {count} 条异常")
        
        return "\n".join(formatted_lines) if formatted_lines else ""


class DefaultFormatter(BaseFormatter):
    """Default formatter for unknown query types"""
    
    def format(self, result_data: Any) -> str:
        """
        Default formatting - general JSON formatting
        """
        content = self._extract_content(result_data)
        
        if isinstance(content, dict):
            if 'content' in content:
                content = content['content']
                if isinstance(content, list):
                    if len(content) == 1:
                        item = content[0]
                        if isinstance(item, str):
                            try:
                                parsed = json.loads(item)
                                return json.dumps(parsed, ensure_ascii=False, indent=2)
                            except:
                                return item
                        else:
                            return json.dumps(item, ensure_ascii=False, indent=2)
                    else:
                        formatted_items = []
                        for idx, item in enumerate(content, 1):
                            if isinstance(item, str):
                                try:
                                    parsed = json.loads(item)
                                    formatted_items.append(f"Item {idx}:\n{json.dumps(parsed, ensure_ascii=False, indent=2)}")
                                except:
                                    formatted_items.append(f"Item {idx}: {item}")
                            else:
                                formatted_items.append(f"Item {idx}:\n{json.dumps(item, ensure_ascii=False, indent=2)}")
                        return "\n".join(formatted_items)
                else:
                    return str(content)
            else:
                return json.dumps(content, ensure_ascii=False, indent=2)
        elif isinstance(content, list):
            return json.dumps(content, ensure_ascii=False, indent=2)
        elif isinstance(content, str):
            try:
                parsed = json.loads(content)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except:
                return content
        else:
            return str(content) if content else ""


# Formatter registry
FORMATTER_REGISTRY: Dict[str, BaseFormatter] = {
    'metrics-formatter': MetricsFormatter(),
    'atms-logs-formatter': AtmsLogsFormatter(),
    'ingress-logs-formatter': IngressLogsFormatter(),
    'general-logs-formatter': GeneralLogsFormatter(),
    'default': DefaultFormatter(),
}


def get_formatter(formatter_name: str = None, tool_name: str = None) -> BaseFormatter:
    """
    Get formatter by name or infer from tool name
    
    Args:
        formatter_name: Formatter name from query config (e.g., 'metrics-formatter')
        tool_name: Tool name to infer formatter type
        
    Returns:
        Formatter instance
    """
    # First, try to get formatter by explicit name
    if formatter_name:
        formatter_name_lower = formatter_name.lower()
        if formatter_name_lower in FORMATTER_REGISTRY:
            return FORMATTER_REGISTRY[formatter_name_lower]
        logger.warning(f"Unknown formatter name: {formatter_name}, falling back to default")
    
    # If no explicit formatter, try to infer from tool name
    if tool_name:
        tool_lower = tool_name.lower()
        if 'metric' in tool_lower or 'prometheus' in tool_lower:
            return FORMATTER_REGISTRY['metrics-formatter']
        elif 'log' in tool_lower or 'elasticsearch' in tool_lower:
            return FORMATTER_REGISTRY['general-logs-formatter']
    
    # Default formatter
    return FORMATTER_REGISTRY['default']


def format_query_result(result_data: Any, formatter_name: str = None, tool_name: str = None) -> str:
    """
    Format query result using the appropriate formatter
    
    Args:
        result_data: Query result data
        formatter_name: Formatter name from query config
        tool_name: Tool name to infer formatter type
        
    Returns:
        Formatted string
    """
    formatter = get_formatter(formatter_name, tool_name)
    return formatter.format(result_data)

