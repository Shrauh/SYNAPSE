const API = "http://localhost:8000/api/v1";

export async function getK8sPods(): Promise<any> {
  const res = await fetch(`${API}/k8s/pods`);
  if (!res.ok) throw new Error('Failed to fetch pods');
  return res.json();
}

export async function injectK8sFault(service: string, faultType: string = 'pod_kill'): Promise<any> {
  const res = await fetch(`${API}/k8s/inject-fault`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, fault_type: faultType })
  });
  if (!res.ok) throw new Error('Failed to inject fault');
  return res.json();
}

export async function recoverK8sService(service: string, action: string = 'restart_pod'): Promise<any> {
  const res = await fetch(`${API}/k8s/recover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, action })
  });
  if (!res.ok) throw new Error('Recovery failed');
  return res.json();
}

export * from "./api/endpoints";
