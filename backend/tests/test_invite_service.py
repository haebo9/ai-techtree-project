from app.services.invite_service import (
    create_invite_session_token,
    generate_invite_code,
    mask_invite_code,
    normalize_invite_code,
    parse_invite_session_token,
    public_invite_info,
)


def test_invite_code_normalization_and_masking():
    assert normalize_invite_code(" tt-abcd 1234 ") == "TT-ABCD1234"
    assert mask_invite_code("TT-ABCD-1234") == "TT-***234"


def test_generate_invite_code_uses_techtree_prefix_and_seven_chars():
    code = generate_invite_code()

    assert code.startswith("TECHTREE-")
    assert len(code.removeprefix("TECHTREE-")) == 7


def test_invite_session_token_roundtrip():
    token = create_invite_session_token(
        {
            "code": "TT-ABCD-1234",
            "name": "홍길동",
        }
    )

    session = parse_invite_session_token(token)

    assert session is not None
    assert session.code == "TT-ABCD-1234"
    assert session.name == "홍길동"


def test_public_invite_info_excludes_plain_code():
    info = public_invite_info(
        {
            "code": "TT-SECRET",
            "name": "관리용 이름",
            "status": "active",
            "use_count": 0,
            "use_max": 1,
        }
    )

    assert "code" not in info
    assert "name" not in info
    assert info["status"] == "active"
    assert info["use_count"] == 0
    assert info["use_max"] == 1
