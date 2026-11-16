"""Supabase 연결과 로그인."""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

from shop.errors import ServiceError

load_dotenv()

def new_client() -> Client:
    """로그인 전의 빈 클라이언트. Publishable 키로만 만든다."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise RuntimeError(".env 에 SUPABASE_URL · SUPABASE_PUBLISHABLE_KEY 를 채우세요.")
    return create_client(url, key)

def login(email: str, password: str) -> Client:
    """이메일·비밀번호로 로그인한 클라이언트를 돌려준다."""
    client = new_client()
    try:
        client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as error:
        raise ServiceError(f"로그인 실패 ({email}): {error}") from error
    return client

def current_user(client: Client):
    """로그인한 사용자 객체. 로그인 안 됐으면 ServiceError."""
    try:
        response = client.auth.get_user()
    except Exception:
        response = None
    if response is None or response.user is None:
        raise ServiceError("로그인이 필요합니다.")
    return response.user
