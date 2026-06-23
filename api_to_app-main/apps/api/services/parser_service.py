from __future__ import annotations
import json, re, zipfile, uuid, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml
from fastapi import UploadFile, HTTPException
from storage.db import conn
from core.config import settings

MAX_ZIP_FILES = 1200
MAX_FILE_SIZE = 450_000
READ_EXT = {'.md','.txt','.json','.yaml','.yml','.py','.ts','.tsx','.js','.jsx','.svelte','.env','.toml'}
KEY_NAMES = {'openapi.json','swagger.json','openapi.yaml','openapi.yml','swagger.yaml','swagger.yml','postman_collection.json','README.md','package.json','requirements.txt','main.py'}

class ParserService:
    def upload(self, file: UploadFile) -> Dict[str, Any]:
        raw = file.file.read()
        session_id = uuid.uuid4().hex[:12]
        name = file.filename or 'uploaded-api'
        root = settings.storage_dir / 'uploads' / session_id
        root.mkdir(parents=True, exist_ok=True)
        saved = root / name
        saved.write_bytes(raw)
        files: List[Tuple[str,str,int,str]] = []
        if name.lower().endswith('.zip'):
            self._safe_extract(saved, root / 'repo')
            files = self._collect_files(root / 'repo')
            kind = 'repository_zip'
        else:
            text = raw.decode('utf-8', errors='ignore')
            kind = self._kind_for(name, text)
            files = [(name, kind, len(raw), text[:MAX_FILE_SIZE])]
        endpoints = self.extract_endpoints({p:c for p,_,_,c in files})
        default_targets = self.default_targets(files)
        stack = self.detect_stack(files)
        with conn() as c:
            c.execute('INSERT INTO sessions(id,name,kind,created_at,file_count,endpoint_count) VALUES (?,?,?,?,?,?)', (session_id,name,kind,datetime.now(timezone.utc).isoformat(),len(files),len(endpoints)))
            for p,k,s,content in files:
                c.execute('INSERT OR REPLACE INTO files(session_id,path,kind,size,content) VALUES (?,?,?,?,?)',(session_id,p,k,s,content))
        return {'session_id':session_id,'name':name,'kind':kind,'file_count':len(files),'endpoint_count':len(endpoints),'detected_stack':stack,'default_targets':default_targets}

    def _safe_extract(self, zip_path: Path, dest: Path):
        if dest.exists(): shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            infos = z.infolist()
            if len(infos) > MAX_ZIP_FILES: raise HTTPException(400, 'ZIP contains too many files')
            for info in infos:
                target = (dest / info.filename).resolve()
                if not str(target).startswith(str(dest.resolve())): raise HTTPException(400, 'Unsafe ZIP path detected')
                if not info.is_dir() and info.file_size > 2_000_000: continue
            z.extractall(dest)

    def _collect_files(self, root: Path) -> List[Tuple[str,str,int,str]]:
        out=[]
        for p in root.rglob('*'):
            if not p.is_file(): continue
            if any(part in {'node_modules','.git','.venv','dist','build','.svelte-kit','__pycache__'} for part in p.parts): continue
            rel=str(p.relative_to(root)).replace('\\','/')
            if p.suffix.lower() not in READ_EXT and p.name not in KEY_NAMES: continue
            size=p.stat().st_size
            if size>MAX_FILE_SIZE: continue
            text=p.read_text(errors='ignore')
            out.append((rel,self._kind_for(rel,text),size,text))
        return sorted(out, key=lambda x: (0 if x[0].split('/')[-1] in KEY_NAMES else 1, x[0]))[:500]

    def _kind_for(self, path: str, text: str) -> str:
        low=path.lower()
        if low.endswith(('.yaml','.yml','.json')) and ('openapi' in text[:2000].lower() or 'swagger' in text[:2000].lower()): return 'openapi_spec'
        if low.endswith('.json') and 'postman' in text[:3000].lower(): return 'postman_collection'
        if low.endswith('.py') and ('@app.' in text or 'APIRouter' in text): return 'fastapi_routes'
        if low.endswith(('.ts','.js')) and ('router.' in text or 'app.get(' in text or 'app.post(' in text): return 'node_routes'
        if low.endswith('.md'): return 'api_docs'
        if low.endswith('.json'): return 'json'
        return 'source'

    def default_targets(self, files):
        preferred=[]
        for p,k,_,_ in files:
            base=p.split('/')[-1]
            if k in {'openapi_spec','postman_collection','fastapi_routes','node_routes','api_docs'} or base in KEY_NAMES:
                preferred.append(p)
        return preferred[:40]

    def detect_stack(self, files):
        names=' '.join(p.lower() for p,_,_,_ in files)
        content='\n'.join(c[:2000].lower() for _,_,_,c in files[:80])
        stack=[]
        if 'fastapi' in content or 'main.py' in names: stack.append('FastAPI')
        if 'svelte' in content or 'svelte.config' in names: stack.append('SvelteKit')
        if 'openapi' in content or 'swagger' in content: stack.append('OpenAPI')
        if 'postman' in content: stack.append('Postman')
        if 'express' in content: stack.append('Express')
        return stack or ['API documentation']

    def files(self, session_id: str):
        with conn() as c:
            rows=c.execute('SELECT path,kind,size FROM files WHERE session_id=? ORDER BY path',(session_id,)).fetchall()
            full=c.execute('SELECT path,kind,size,content FROM files WHERE session_id=?',(session_id,)).fetchall()
        return {'files':[dict(r) for r in rows], 'default_targets': self.default_targets([(r['path'],r['kind'],r['size'],r['content']) for r in full])}

    def session_files(self, session_id: str, target_files: List[str] | None = None) -> Dict[str,str]:
        with conn() as c:
            if target_files:
                q=','.join('?' for _ in target_files)
                rows=c.execute(f'SELECT path,content FROM files WHERE session_id=? AND path IN ({q})',[session_id,*target_files]).fetchall()
            else:
                rows=c.execute('SELECT path,content FROM files WHERE session_id=?',(session_id,)).fetchall()
        return {r['path']: r['content'] for r in rows}

    def extract_endpoints(self, files: Dict[str,str]) -> List[Dict[str,Any]]:
        endpoints=[]
        for path,text in files.items():
            if not text.strip(): continue
            low=path.lower()
            if low.endswith(('.json','.yaml','.yml')):
                endpoints += self._from_spec(text,path)
                endpoints += self._from_postman(text,path)
            if low.endswith('.py'):
                endpoints += self._from_fastapi(text,path)
            if low.endswith(('.ts','.js')):
                endpoints += self._from_node(text,path)
            if low.endswith('.md'):
                endpoints += self._from_markdown(text,path)
        # dedupe
        seen=set(); out=[]
        for e in endpoints:
            key=(e['method'],e['path'])
            if key not in seen:
                seen.add(key); out.append(e)
        return out[:120]

    def _from_spec(self,text,path):
        try:
            data=json.loads(text) if text.lstrip().startswith('{') else yaml.safe_load(text)
        except Exception: return []
        if not isinstance(data,dict) or 'paths' not in data: return []
        out=[]
        for p, ops in (data.get('paths') or {}).items():
            if not isinstance(ops,dict): continue
            for m,v in ops.items():
                if m.lower() not in {'get','post','put','patch','delete'}: continue
                v=v or {}
                out.append({'method':m.upper(),'path':p,'operation_id':v.get('operationId') or self._op(m,p),'summary':v.get('summary') or v.get('description') or f'{m.upper()} {p}','auth_required':bool(data.get('security') or v.get('security')),'request_schema':v.get('requestBody') or {},'response_schema':(v.get('responses') or {}).get('200') or {},'source':path})
        return out

    def _from_postman(self,text,path):
        try: data=json.loads(text)
        except Exception: return []
        if 'item' not in data or 'postman' not in json.dumps(data)[:2000].lower(): return []
        out=[]
        def walk(items):
            for item in items or []:
                if 'item' in item: walk(item['item'])
                req=item.get('request') if isinstance(item,dict) else None
                if not req: continue
                method=(req.get('method') or 'GET').upper()
                url=req.get('url') or {}
                raw=url.get('raw') if isinstance(url,dict) else str(url)
                p='/' + '/'.join(url.get('path') or []) if isinstance(url,dict) and url.get('path') else raw
                p=re.sub(r'^https?://[^/]+','',p) or '/'
                out.append({'method':method,'path':p,'operation_id':self._op(method,p),'summary':item.get('name') or f'{method} {p}','auth_required':bool(req.get('auth') or data.get('auth')),'request_schema':{},'response_schema':{},'source':path})
        walk(data.get('item'))
        return out

    def _from_fastapi(self,text,path):
        out=[]
        pat=re.compile(r'@(?:app|router)\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']')
        for m,p in pat.findall(text):
            out.append({'method':m.upper(),'path':p,'operation_id':self._op(m,p),'summary':f'{m.upper()} {p}','auth_required':'Depends(' in text[max(0,text.find(p)-400):text.find(p)+800],'request_schema':{},'response_schema':{},'source':path})
        return out

    def _from_node(self,text,path):
        out=[]
        pat=re.compile(r'(?:app|router)\.(get|post|put|patch|delete)\([`"\']([^`"\']+)[`"\']')
        for m,p in pat.findall(text):
            out.append({'method':m.upper(),'path':p,'operation_id':self._op(m,p),'summary':f'{m.upper()} {p}','auth_required':'auth' in text[max(0,text.find(p)-300):text.find(p)+600].lower(),'request_schema':{},'response_schema':{},'source':path})
        return out

    def _from_markdown(self,text,path):
        out=[]
        pat=re.compile(r'\b(GET|POST|PUT|PATCH|DELETE)\s+(/[^\s`\)]+)', re.I)
        for m,p in pat.findall(text):
            out.append({'method':m.upper(),'path':p,'operation_id':self._op(m,p),'summary':f'{m.upper()} {p}','auth_required':'authorization' in text.lower() or 'bearer' in text.lower(),'request_schema':{},'response_schema':{},'source':path})
        return out

    def _op(self,m,p):
        slug=re.sub(r'[^a-zA-Z0-9]+','_',p).strip('_').lower() or 'root'
        return f'{str(m).lower()}_{slug}'
