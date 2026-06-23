from __future__ import annotations
import json, uuid, re
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests, yaml
from core.config import settings
from storage.db import conn
from services.parser_service import ParserService

SKILL_INFLUENCES = [
  'api-design-principles: resource naming, status codes, pagination and developer usability',
  'api-documentation-generator: endpoint examples, auth notes, request/response documentation',
  'api-patterns: REST/GraphQL style decisions, versioning, response envelopes',
  'app-builder: app architecture, scaffold manifest and feature decomposition',
  'frontend-api-integration-patterns: request cancellation, error normalization and UI state handling',
  'sveltekit: SvelteKit route/page conventions and env-safe browser API configuration',
  'fastapi-pro: optional backend proxy/service patterns',
  'api-testing-observability-api-mock: mock handlers and integration tests',
  'api-security-best-practices: auth, CORS, secret handling, input validation and rate-limit notes',
]

class GeneratorService:
    def __init__(self):
        self.parser = ParserService()

    def health(self):
        with conn() as c:
            s=c.execute('SELECT COUNT(*) n FROM sessions').fetchone()['n']
            g=c.execute('SELECT COUNT(*) n FROM generations').fetchone()['n']
        provider=(settings.llm_provider or 'offline').lower()
        enabled=(provider=='deepseek' and bool(settings.deepseek_api_key)) or (provider=='gemini' and bool(settings.gemini_api_key))
        return {'ok': True, 'provider': provider, 'ai_enabled': enabled, 'sessions': s, 'generations': g}

    def generate(self, payload: Dict[str,Any]):
        files=self.parser.session_files(payload['session_id'], payload.get('target_files') or [])
        endpoints=self.parser.extract_endpoints(files)
        if not endpoints:
            endpoints=[{'method':'GET','path':'/health','operation_id':'get_health','summary':'Health check endpoint inferred as a starter contract','auth_required':False,'request_schema':{},'response_schema':{},'source':'fallback'}]
        decisions=payload.get('human_decisions') or self.default_decisions(payload, endpoints)
        artifacts=self._artifacts(payload, endpoints, files, decisions)
        summary=self._summary(payload,endpoints,decisions)
        if payload.get('use_llm'):
            summary=self._llm_summary(payload,endpoints,decisions) or summary
        manifest=self._manifest(payload,endpoints,artifacts)
        report=self._markdown_report(payload,endpoints,decisions,artifacts,manifest,summary)
        generation_id=uuid.uuid4().hex[:12]
        result={'generation_id':generation_id,'summary':summary,'endpoints':endpoints,'decisions':decisions,'artifacts':artifacts,'build_manifest':manifest,'markdown_report':report}
        with conn() as c:
            c.execute('INSERT INTO generations(id,session_id,objective,app_name,artifact_json,created_at) VALUES (?,?,?,?,?,?)',(generation_id,payload['session_id'],payload.get('objective',''),payload.get('app_name','Generated API App'),json.dumps(result),datetime.now(timezone.utc).isoformat()))
        return result

    def default_decisions(self,payload,endpoints):
        return [
            {'id':'auth','question':'Does this API require authenticated requests?','answer':'yes' if any(e.get('auth_required') for e in endpoints) else 'no'},
            {'id':'proxy','question':'Should browser requests go through a backend proxy for secrets/CORS?','answer':'yes' if payload.get('api_style') in {'backend_proxy','hybrid'} else 'no'},
            {'id':'writes','question':'Should mutating endpoints require a confirmation UI?','answer':'yes' if any(e['method'] in {'POST','PUT','PATCH','DELETE'} for e in endpoints) else 'no'},
            {'id':'tests','question':'Generate integration tests and mock responses?','answer':'yes'},
        ]

    def _summary(self,payload,endpoints,decisions):
        return f"Generated a production {payload.get('framework','sveltekit')} app plan for {len(endpoints)} API endpoints with typed client, UI scaffold, tests, environment matrix and implementation README."

    def _artifacts(self,payload,endpoints,files,decisions):
        return [
            {'name':'src/lib/api/client.ts','language':'typescript','content':self._client_ts(endpoints,payload,decisions)},
            {'name':'src/routes/+page.svelte','language':'svelte','content':self._page_svelte(endpoints,payload,decisions)},
            {'name':'src/lib/api/types.ts','language':'typescript','content':self._types_ts(endpoints)},
            {'name':'tests/api-contract.spec.ts','language':'typescript','content':self._tests(endpoints)},
            {'name':'BACKEND_PROXY_PLAN.md','language':'markdown','content':self._proxy_plan(endpoints,payload,decisions)},
            {'name':'ENV_MATRIX.md','language':'markdown','content':self._env_matrix(payload,decisions)},
            {'name':'README_IMPLEMENTATION.md','language':'markdown','content':self._implementation_readme(payload,endpoints,decisions)},
            {'name':'build-manifest.json','language':'json','content':json.dumps(self._manifest(payload,endpoints,[]),indent=2)},
            {'name':'openapi-endpoint-map.yaml','language':'yaml','content':yaml.safe_dump({'endpoints':endpoints},sort_keys=False)},
        ]

    def _client_ts(self,endpoints,payload,decisions):
        lines=["import type { ApiError, RequestOptions } from './types';",'',"const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\\/$/, '');",'',"async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {","  const controller = new AbortController();","  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 30000);","  try {","    const headers: Record<string, string> = { 'content-type': 'application/json', ...(options.headers ?? {}) };","    if (options.token) headers.authorization = `Bearer ${options.token}`;","    const res = await fetch(`${API_BASE}${path}`, { method: options.method ?? 'GET', headers, body: options.body ? JSON.stringify(options.body) : undefined, signal: controller.signal });","    const text = await res.text();","    const data = text ? JSON.parse(text) : null;","    if (!res.ok) { const err: ApiError = { status: res.status, message: data?.message ?? data?.detail ?? res.statusText, details: data }; throw err; }","    return data as T;","  } finally { window.clearTimeout(timeout); }","}",'','export const api = {']
        for e in endpoints[:60]:
            name=self._safe_name(e['operation_id'])
            body=', body?: unknown' if e['method'] in {'POST','PUT','PATCH'} else ''
            lines.append(f"  {name}: (token?: string{body}) => request<unknown>(`{e['path']}`, {{ method: '{e['method']}', token{', body' if body else ''} }}),")
        lines.append('};\n')
        return '\n'.join(lines)

    def _page_svelte(self,endpoints,payload,decisions):
        first=endpoints[0]
        mutating=any(e['method'] in {'POST','PUT','PATCH','DELETE'} for e in endpoints)
        return f'''<script lang="ts">
  import {{ api }} from '$lib/api/client';
  let token = $state('');
  let loading = $state(false);
  let error = $state('');
  let output = $state<unknown>(null);

  async function runPrimaryAction() {{
    loading = true;
    error = '';
    try {{
      output = await api.{self._safe_name(first['operation_id'])}(token || undefined);
    }} catch (e) {{
      error = e instanceof Error ? e.message : JSON.stringify(e);
    }} finally {{
      loading = false;
    }}
  }}
</script>

<svelte:head><title>{payload.get('app_name','Generated API App')}</title></svelte:head>

<main class="api-app-shell">
  <section class="hero">
    <p class="eyebrow">Generated API interface</p>
    <h1>{payload.get('app_name','Generated API App')}</h1>
    <p>Production starter UI for {len(endpoints)} mapped endpoints. Start with <code>{first['method']} {first['path']}</code>, then extend the generated client and route sections.</p>
  </section>

  <section class="panel">
    <label for="token">Bearer token {{optional}}</label>
    <input id="token" bind:value={{token}} placeholder="Paste token for authenticated APIs" />
    <button type="button" onclick={{runPrimaryAction}} disabled={{loading}}>{{loading ? 'Calling API…' : 'Run primary endpoint'}}</button>
    {{#if error}}<p class="error">{{error}}</p>{{/if}}
    {{#if output}}<pre>{{JSON.stringify(output, null, 2)}}</pre>{{/if}}
  </section>

  <section class="endpoint-grid">
    {{#each {json.dumps([{k:e[k] for k in ['method','path','summary']} for e in endpoints[:24]])} as endpoint}}
      <article>
        <strong>{{endpoint.method}}</strong>
        <code>{{endpoint.path}}</code>
        <p>{{endpoint.summary}}</p>
      </article>
    {{/each}}
  </section>
</main>
'''

    def _types_ts(self,endpoints):
        return '''export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface RequestOptions {
  method?: HttpMethod;
  token?: string;
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
}

export interface ApiError {
  status: number;
  message: string;
  details?: unknown;
}

export interface EndpointDefinition {
  method: HttpMethod;
  path: string;
  operationId: string;
  authRequired: boolean;
}
'''

    def _tests(self,endpoints):
        checks='\n'.join([f"  expect(endpointMap).toContain('{e['method']} {e['path']}');" for e in endpoints[:25]])
        return f'''import {{ describe, expect, it }} from 'vitest';

const endpointMap = [
{chr(10).join([f"  '{e['method']} {e['path']}'," for e in endpoints[:60]])}
];

describe('generated API contract', () => {{
  it('contains expected mapped endpoints', () => {{
{checks or "    expect(endpointMap.length).toBeGreaterThan(0);"}
  }});
}});
'''

    def _proxy_plan(self,endpoints,payload,decisions):
        return '# Backend Proxy Plan\n\nUse a backend proxy when the API requires server-only credentials, signed requests, or CORS isolation.\n\n## Routes to proxy\n\n' + '\n'.join([f"- `{e['method']} {e['path']}` — {'auth required' if e.get('auth_required') else 'public or token delegated'}" for e in endpoints[:80]]) + '\n\n## FastAPI pattern\n\n- Keep upstream secrets in server `.env`, never in `VITE_*`.\n- Validate request body with Pydantic models.\n- Normalize upstream errors before returning to the browser.\n- Add rate limiting for mutating endpoints.\n'

    def _env_matrix(self,payload,decisions):
        return '''# Environment Variable Matrix

| Variable | Runtime | Required | Purpose | Browser exposed |
| --- | --- | --- | --- | --- |
| `VITE_API_BASE_URL` | frontend | yes | Browser-safe API base URL or proxy base URL | yes |
| `UPSTREAM_API_BASE_URL` | backend proxy | when proxying | Server-only upstream API root | no |
| `UPSTREAM_API_KEY` | backend proxy | when using API keys | Server-only credential for upstream API | no |
| `AUTH_TOKEN_ISSUER` | backend/frontend | optional | Token issuer or auth provider reference | no |

Do not prefix secrets with `VITE_`, `NEXT_PUBLIC_`, or any browser-exposed prefix.
'''

    def _implementation_readme(self,payload,endpoints,decisions):
        return f'''# {payload.get('app_name','Generated API App')} Implementation Guide

## Objective

{payload.get('objective','Build a production app from the uploaded API contract.')}

## Endpoint coverage

{chr(10).join([f"- `{e['method']} {e['path']}` — {e['summary']}" for e in endpoints[:80]])}

## Build sequence

1. Create the SvelteKit app shell and install dependencies.
2. Add `src/lib/api/types.ts` and `src/lib/api/client.ts` from the generated artifacts.
3. Set `VITE_API_BASE_URL` in `.env`.
4. If secrets or CORS are involved, implement the backend proxy plan before connecting the browser directly.
5. Build UI sections around the generated endpoint map.
6. Add contract tests from `tests/api-contract.spec.ts`.
7. Run smoke tests against staging before production.

## Human decisions applied

{chr(10).join([f"- {d['question']} **{d['answer'].upper()}**" for d in decisions])}

## Security rules

- Never expose upstream API keys in browser code.
- Add confirmation UI for mutating endpoints.
- Normalize API errors to avoid leaking stack traces.
- Enforce request timeouts and cancellation.
'''

    def _manifest(self,payload,endpoints,artifacts):
        return {'app_name':payload.get('app_name'),'framework':payload.get('framework'),'api_style':payload.get('api_style'),'endpoint_count':len(endpoints),'generated_files':[a.get('name') for a in artifacts] if artifacts else ['src/lib/api/client.ts','src/routes/+page.svelte','README_IMPLEMENTATION.md'],'skill_influences':SKILL_INFLUENCES}

    def _markdown_report(self,payload,endpoints,decisions,artifacts,manifest,summary):
        return f'''# API-to-App Generation Report

{summary}

## Endpoint map

{chr(10).join([f"- `{e['method']} {e['path']}` — {e['summary']}" for e in endpoints[:120]])}

## Human-in-the-loop decisions

{chr(10).join([f"- {d['question']} **{d['answer'].upper()}**" for d in decisions])}

## Generated artifacts

{chr(10).join([f"- `{a['name']}`" for a in artifacts])}

## Implementation order

1. Review endpoint map and auth assumptions.
2. Add environment variables.
3. Copy generated client/types.
4. Copy Svelte page scaffold and adapt UI copy.
5. Add backend proxy if required.
6. Run contract tests and smoke tests.
'''

    def _llm_summary(self,payload,endpoints,decisions):
        provider=(settings.llm_provider or 'offline').lower()
        if provider=='deepseek' and settings.deepseek_api_key:
            try:
                resp=requests.post('https://api.deepseek.com/chat/completions',headers={'Authorization':f'Bearer {settings.deepseek_api_key}','Content-Type':'application/json'},json={'model':settings.deepseek_model,'messages':[{'role':'system','content':'Return one concise production engineering summary for an API-to-app generation result.'},{'role':'user','content':json.dumps({'objective':payload.get('objective'),'endpoints':endpoints[:20],'decisions':decisions})}], 'temperature':0.2},timeout=35)
                resp.raise_for_status(); return resp.json()['choices'][0]['message']['content'].strip()
            except Exception: return None
        return None

    def _safe_name(self,s):
        s=re.sub(r'[^a-zA-Z0-9_]+','_',s).strip('_') or 'call_api'
        parts=s.split('_')
        return parts[0].lower()+''.join(p[:1].upper()+p[1:] for p in parts[1:])
