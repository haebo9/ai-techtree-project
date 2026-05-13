from pydantic import BaseModel, Field


class InviteVerifyRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=120)


class InvitePublicInfo(BaseModel):
    status: str = ""
    use_count: int = 0
    use_max: int = 1


class InviteVerifyResponse(BaseModel):
    authenticated: bool
    invite: InvitePublicInfo


class InviteSessionResponse(BaseModel):
    authenticated: bool
    invite: InvitePublicInfo | None = None
