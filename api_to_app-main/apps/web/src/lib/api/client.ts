const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8007').replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${JSON.stringify(data)}`);
  return data as T;
}

export type Stage = 'upload' | 'scope' | 'decide' | 'artifacts';
export interface Health { ok: boolean; provider: string; ai_enabled: boolean; sessions: number; generations: number }
export interface UploadedApi { session_id: string; name: string; kind: string; file_count: number; endpoint_count: number; detected_stack: string[]; default_targets: string[] }
export interface ApiFile { path: string; kind: string; size: number }
export interface FileList { files: ApiFile[]; default_targets: string[] }
export interface Endpoint { method: string; path: string; operation_id: string; summary: string; auth_required: boolean; source: string }
export interface HumanDecision { id: string; question: string; answer: 'yes' | 'no' }
export interface Artifact { name: string; language: string; content: string }
export interface GenerateResponse { generation_id: string; summary: string; endpoints: Endpoint[]; decisions: HumanDecision[]; artifacts: Artifact[]; build_manifest: Record<string, unknown>; markdown_report: string }

export const api = {
  health: () => request<Health>('/api/v1/api-gen/health'),
  upload: (file: File) => { const form = new FormData(); form.append('file', file); return request<UploadedApi>('/api/v1/api-gen/upload', { method: 'POST', body: form }); },
  files: (sessionId: string) => request<FileList>(`/api/v1/api-gen/files/${sessionId}`),
  generate: (payload: { session_id: string; app_name: string; objective: string; target_files: string[]; framework: string; api_style: string; human_decisions: HumanDecision[]; use_llm: boolean }) => request<GenerateResponse>('/api/v1/api-gen/generate', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) }),
  skills: () => request<{ skills: string[] }>('/api/v1/api-gen/skills')
};
