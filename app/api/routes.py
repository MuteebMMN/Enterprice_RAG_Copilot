from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.core.deps import CurrentUser, require_role
from app.core.ratelimit import chat_rate_limit
from pydantic import BaseModel, Field
from app.core.config import get_settings
from app.rag.workflow import ask
from app.rag.vectorstore import add_documents, VISIBILITIES
from app.services.ingestion import load_file, chunk_documents, SUPPORTED
from app.services.audit import write_audit

router=APIRouter(prefix="/api")

settings= get_settings()

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=3000)


@router.post("/chat")
def chat(payload: ChatRequest, user: CurrentUser = Depends(chat_rate_limit)):
    try:
        result = ask(payload.question, user)
        write_audit(payload.question, result["source_used"], result.get("trace", []), user, result.get("guardrail"))

        return {
            "answer": result["answer"],
            "source_used": result["source_used"],
            "trace": result.get("trace", []),
            "citations": result.get("citations", []),
            "rewritten_query": result.get("current_query", payload.question),

        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc



@router.post("/ingest")
def ingest(
    file: UploadFile = File(...),
    visibility: str = Form("all"),
    user: CurrentUser = Depends(require_role("admin")),
):
    if visibility not in VISIBILITIES:
        raise HTTPException(status_code=400, detail=f"visibility must be one of: {', '.join(VISIBILITIES)}")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Supported: {', '.join(sorted(SUPPORTED))}")
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / Path(file.filename).name
    dest.write_bytes(file.file.read())
    docs = load_file(dest)
    chunks = chunk_documents(docs)
    ids = add_documents(chunks, visibility)
    return {"message": "Document indexed", "file": dest.name, "visibility": visibility, "chunks": len(chunks), "ids_created": len(ids)}