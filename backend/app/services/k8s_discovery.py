import subprocess
import json
import logging
from typing import List, Dict, Any, Optional
import networkx as nx

logger = logging.getLogger(__name__)

def _kubectl(cmd: str) -> Optional[Any]:
    try:
        result = subprocess.run(['kubectl'] + cmd.split(), capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        logger.error(f"kubectl error: {result.stderr}")
    except Exception as e:
        logger.error(f"kubectl execution failed: {e}")
    return None

class KubernetesDiscovery:
    def __init__(self):
        try:
            from kubernetes import client, config
            config.load_kube_config()
            self.v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self.use_client = True
        except ImportError:
            self.use_client = False
            logger.info("kubernetes python client not found, falling back to kubectl")
        except Exception as e:
            self.use_client = False
            logger.info(f"Failed to init kubernetes client, falling back to kubectl: {e}")

    def discover_services(self) -> List[str]:
        if self.use_client:
            try:
                deps = self.v1.list_namespaced_deployment(namespace="default")
                return [dep.metadata.name for dep in deps.items]
            except Exception as e:
                logger.error(f"K8s API error: {e}")
                
        data = _kubectl("get deployments -n default -o json")
        if not data or 'items' not in data:
            return []
        
        services = []
        for item in data['items']:
            services.append(item['metadata']['name'])
        return services

    def discover_topology(self) -> List[Dict[str, str]]:
        if self.use_client:
            # For brevity, implementing fallback primarily since it covers the requirements
            pass
            
        data = _kubectl("get deployments -n default -o json")
        if not data or 'items' not in data:
            return []

        edges = []
        for item in data['items']:
            service = item['metadata']['name']
            containers = item.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
            for container in containers:
                for env in container.get('env', []):
                    if env['name'] == 'DOWNSTREAM_SERVICES':
                        downstreams = env['value'].split(',')
                        for ds in downstreams:
                            if ds.strip():
                                edges.append({"source": service, "target": ds.strip()})
        return edges

    def get_pod_status(self, service_name: str) -> List[Dict[str, str]]:
        data = _kubectl(f"get pods -l app={service_name} -n default -o json")
        if not data or 'items' not in data:
            return []
        
        statuses = []
        for item in data['items']:
            pod_name = item['metadata']['name']
            status = item.get('status', {}).get('phase', 'Unknown')
            # Check for CrashLoopBackOff
            container_statuses = item.get('status', {}).get('containerStatuses', [])
            for cs in container_statuses:
                if cs.get('state', {}).get('waiting', {}).get('reason') == 'CrashLoopBackOff':
                    status = 'CrashLoopBackOff'
                    break
            statuses.append({
                "pod_name": pod_name,
                "status": status
            })
        return statuses

    def build_dynamic_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        services = self.discover_services()
        for svc in services:
            graph.add_node(svc)
        
        edges = self.discover_topology()
        for edge in edges:
            graph.add_edge(edge['source'], edge['target'])
            
        return graph

k8s_discovery = KubernetesDiscovery()
