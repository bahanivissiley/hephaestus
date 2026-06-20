from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Conversation, User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationPayload(BaseModel):
    title: str | None = None
    messages: list[dict] = []
    carnet: dict = {}
    state: dict = {}


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: str


class ConversationDetail(ConversationSummary):
    messages: list[dict]
    carnet: dict
    state: dict


def _title_from_state(state: dict, fallback: str = "Nouveau voyage") -> str:
    dest = state.get("destination")
    duree = state.get("duree_jours")
    if dest and duree:
        return f"{dest} · {duree} jours"
    if dest:
        return str(dest)
    return fallback


def _summary(c: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=str(c.id), title=c.title, updated_at=c.updated_at.isoformat() if c.updated_at else ""
    )


def _detail(c: Conversation) -> ConversationDetail:
    return ConversationDetail(
        id=str(c.id),
        title=c.title,
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
        messages=c.messages or [],
        carnet=c.carnet or {},
        state=c.state or {},
    )


def _get_owned(conversation_id: str, user: User, db: Session) -> Conversation:
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conv


@router.get("", response_model=list[ConversationSummary])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [_summary(c) for c in convs]


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _detail(_get_owned(conversation_id, user, db))


@router.post("", response_model=ConversationDetail, status_code=201)
def create_conversation(
    payload: ConversationPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = Conversation(
        user_id=user.id,
        title=payload.title or _title_from_state(payload.state),
        messages=payload.messages,
        carnet=payload.carnet,
        state=payload.state,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _detail(conv)


@router.put("/{conversation_id}", response_model=ConversationDetail)
def update_conversation(
    conversation_id: str,
    payload: ConversationPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _get_owned(conversation_id, user, db)
    conv.messages = payload.messages
    conv.carnet = payload.carnet
    conv.state = payload.state
    conv.title = payload.title or _title_from_state(payload.state, fallback=conv.title)
    db.commit()
    db.refresh(conv)
    return _detail(conv)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    conv = _get_owned(conversation_id, user, db)
    db.delete(conv)
    db.commit()
