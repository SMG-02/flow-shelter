"""Feature routers, mounted at /api (see app/index.py).

Every route here is authenticated (mirroring /auth, which sits outside /api).
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.endpoints import cashflow, dashboard, goals, onboarding, transactions

router = APIRouter(dependencies=[Depends(get_current_user)])

router.include_router(onboarding.router, dependencies=[Depends(get_current_user)])
router.include_router(dashboard.router, dependencies=[Depends(get_current_user)])
router.include_router(cashflow.router, dependencies=[Depends(get_current_user)])
router.include_router(transactions.router, dependencies=[Depends(get_current_user)])
router.include_router(goals.router, dependencies=[Depends(get_current_user)])
