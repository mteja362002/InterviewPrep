"""Read-only Company Intelligence API.

Exposes compiled company artifacts to the frontend and other services. Never
exposes raw markdown. All data originates from compiled JSON artifacts via the
runtime loader.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from company_intelligence.loader import company_intelligence

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("")
async def list_companies():
    """Return the compiled company catalog (registry + version pointers)."""
    return {
        "schema_version": company_intelligence.index().get("schema_version"),
        "companies": company_intelligence.list_companies(),
    }


@router.get("/{company_id}")
async def get_company(company_id: str):
    art = company_intelligence.get_company(company_id)
    if art is None:
        raise HTTPException(status_code=404, detail=f"Unknown company: {company_id}")
    return art


@router.get("/{company_id}/summary")
async def get_company_summary(company_id: str):
    data = company_intelligence.get_summary(company_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Unknown company: {company_id}")
    return data


@router.get("/{company_id}/signals")
async def get_company_signals(company_id: str):
    data = company_intelligence.get_signals(company_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Unknown company: {company_id}")
    return data


@router.get("/{company_id}/metadata")
async def get_company_metadata(company_id: str):
    data = company_intelligence.get_metadata(company_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Unknown company: {company_id}")
    return data
