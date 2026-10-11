from fastapi import APIRouter, Request

from app.schemas.settings import SettingsModel, SettingsUpdate
from app.services.settings import load_settings, save_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsModel)
async def get_settings(request: Request) -> SettingsModel:
    return await load_settings(request.app.state.settings_repo, request.app.state.config)


@router.put("", response_model=SettingsModel)
async def update_settings(payload: SettingsUpdate, request: Request) -> SettingsModel:
    return await save_settings(
        request.app.state.settings_repo, request.app.state.config, payload.model_dump()
    )
