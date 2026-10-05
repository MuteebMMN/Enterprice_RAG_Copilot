from typing import List, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.documents import Document

class RouteDecision(BaseModel):
    route: Literal["kb", "direct", "personal"] = Field(
        description="kb for knowledge questions; personal for the asker's own HR data; direct for greetings/simple chat"
    )

class PersonalNeeds(BaseModel):
    needs: List[Literal["profile", "leave", "salary"]] = Field(
        default_factory=list, description="Which categories of the asker's own HR data the question needs"
    )

class EvidenceGrade(BaseModel):
    grade: Literal["good", "weak"] = Field(description="Whether evidence is sufficient to answer")

class AgentState(TypedDict):
    question: str
    current_query: str
    kb_docs: List[Document]
    web_results: str
    kb_grade: str
    web_grade: str
    answer: str
    source_used: str
    retry_count: int
    trace: List[str]
    citations: List[dict]
    user: dict
    guardrail: dict
    personal_data: dict