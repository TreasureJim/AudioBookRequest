from typing import Annotated, Sequence

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, Query, Security
from sqlmodel import Session

from app.internal.auth.authentication import AnyAuth, DetailedUser 
from app.internal.models import BaseSQLModel, GroupEnum
from app.util.connection import get_connection
from app.util.db import get_session

router = APIRouter(prefix="/metadata", tags=["Recommendations"])

class AuthorMetadata(BaseSQLModel):
    id: int | None
    asin: str | None
    name: str
    save_path: str | None

    serieses: list[Series]

    def get(session: Session):
        select

@router.get("/author/{author_id}")
async def get_author_metadata(
    author_id: int,
    session: Annotated[Session, Depends(get_session)],
    client_session: Annotated[ClientSession, Depends(get_connection)],
    _: Annotated[DetailedUser, Security(AnyAuth(GroupEnum.admin))],
):

