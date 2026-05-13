from fastapi import APIRouter, HTTPException, Request, Response, status

from app.schemas_api.invite import InviteSessionResponse, InviteVerifyRequest, InviteVerifyResponse
from app.services.invite_service import (
    InviteAuthError,
    InviteCodeStore,
    InviteStoreUnavailable,
    clear_invite_cookie,
    create_invite_session_token,
    get_invite_session_from_request,
    notify_invite_verified,
    public_invite_info,
    set_invite_cookie,
)

router = APIRouter()


@router.post("/verify", response_model=InviteVerifyResponse)
async def verify_invite_code(request: InviteVerifyRequest, response: Response):
    try:
        document = InviteCodeStore().consume_code(request.code)
    except InviteAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 사용 가능한 횟수를 초과한 초대코드입니다.",
        )
    except InviteStoreUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="초대코드 인증 저장소를 사용할 수 없습니다.",
        )

    set_invite_cookie(response, create_invite_session_token(document))
    notify_invite_verified(document)
    return {
        "authenticated": True,
        "invite": public_invite_info(document),
    }


@router.get("/session", response_model=InviteSessionResponse)
async def get_invite_session(request: Request, response: Response):
    session = get_invite_session_from_request(request)
    if not session:
        clear_invite_cookie(response)
        return {"authenticated": False, "invite": None}

    return {
        "authenticated": True,
        "invite": {
            "status": "session",
            "use_count": 0,
            "use_max": 1,
        },
    }


@router.post("/logout")
async def logout_invite_session(response: Response):
    clear_invite_cookie(response)
    return {"authenticated": False}
