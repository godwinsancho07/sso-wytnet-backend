from typing import List
from fastapi import APIRouter

from app.api.deps import CurrentUser, DB
from app.schemas.session import SessionRead
from app.services.session import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=List[SessionRead])
async def list_sessions(current_user: CurrentUser, db: DB) -> List[SessionRead]:
    service = SessionService(db)
    sessions = await service.get_active_sessions(current_user.id)
    return [SessionRead.model_validate(s) for s in sessions]


@router.delete("/{session_id}", status_code=204)
async def revoke_session(session_id: str, current_user: CurrentUser, db: DB) -> None:
    service = SessionService(db)
    await service.revoke_session(session_id, current_user.id)


@router.delete("", status_code=204)
async def revoke_all_sessions(current_user: CurrentUser, db: DB) -> None:
    service = SessionService(db)
    await service.revoke_all_sessions(current_user.id)
