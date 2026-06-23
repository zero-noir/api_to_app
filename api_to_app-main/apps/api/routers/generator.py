from fastapi import APIRouter, UploadFile, File
from services.parser_service import ParserService
from services.generator_service import GeneratorService, SKILL_INFLUENCES
from schemas.generator import Health, UploadedApi, FileList, GenerateRequest, GenerateResponse
from storage.db import conn

router = APIRouter(prefix='/api/v1/api-gen', tags=['API to App Generator'])
parser = ParserService()
generator = GeneratorService()

@router.get('/health', response_model=Health)
def health():
    return generator.health()

@router.post('/upload', response_model=UploadedApi)
def upload(file: UploadFile = File(...)):
    return parser.upload(file)

@router.get('/files/{session_id}', response_model=FileList)
def files(session_id: str):
    return parser.files(session_id)

@router.post('/generate', response_model=GenerateResponse)
def generate(payload: GenerateRequest):
    return generator.generate(payload.model_dump())

@router.get('/sessions')
def sessions():
    with conn() as c:
        return {'sessions':[dict(r) for r in c.execute('SELECT * FROM sessions ORDER BY created_at DESC LIMIT 30').fetchall()]}

@router.get('/skills')
def skills():
    return {'skills': SKILL_INFLUENCES}
