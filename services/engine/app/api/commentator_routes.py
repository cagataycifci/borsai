"""Commentator API routes (Phase 9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.commentator import CommentatorReport, CommentatorService

from .deps import get_commentator_service

router = APIRouter(prefix="/api/v1/commentator", tags=["commentator"])

CommentatorDep = Annotated[CommentatorService, Depends(get_commentator_service)]


@router.get("/{symbol}", response_model=CommentatorReport, summary="Consensus commentary")
async def get_commentator_report(
    service: CommentatorDep,
    symbol: str,
    limit: Annotated[int, Query(ge=1, le=30)] = 12,
) -> CommentatorReport:
    return await service.analyze(symbol, limit=limit)
