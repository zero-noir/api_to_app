from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class Health(BaseModel):
    ok: bool
    provider: str
    ai_enabled: bool
    sessions: int
    generations: int

class UploadedApi(BaseModel):
    session_id: str
    name: str
    kind: str
    file_count: int
    endpoint_count: int
    detected_stack: List[str]
    default_targets: List[str]

class ApiFile(BaseModel):
    path: str
    kind: str
    size: int

class FileList(BaseModel):
    files: List[ApiFile]
    default_targets: List[str]

class Endpoint(BaseModel):
    method: str
    path: str
    operation_id: str
    summary: str
    auth_required: bool = False
    request_schema: Dict[str, Any] = Field(default_factory=dict)
    response_schema: Dict[str, Any] = Field(default_factory=dict)
    source: str = 'spec'

class HumanDecision(BaseModel):
    id: str
    question: str
    answer: Literal['yes','no']

class GenerateRequest(BaseModel):
    session_id: str
    app_name: str = 'Generated API App'
    objective: str
    target_files: List[str] = Field(default_factory=list)
    framework: Literal['sveltekit','nextjs','react_vite'] = 'sveltekit'
    api_style: Literal['direct_client','backend_proxy','hybrid'] = 'direct_client'
    human_decisions: List[HumanDecision] = Field(default_factory=list)
    use_llm: bool = True

class Artifact(BaseModel):
    name: str
    language: str
    content: str

class GenerateResponse(BaseModel):
    generation_id: str
    summary: str
    endpoints: List[Endpoint]
    decisions: List[HumanDecision]
    artifacts: List[Artifact]
    build_manifest: Dict[str, Any]
    markdown_report: str
