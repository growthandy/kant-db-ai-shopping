"""회원(members) CRUD."""

from datetime import datetime, timezone

from supabase import Client

from shop.client import current_user
from shop.errors import db_errors, first_or_error

COLUMNS = "id, name, phone, zip_code, address, address_detail, member_type, marketing_agreed, created_at, updated_at"

class MemberService:
    def __init__(self, client: Client):
        self.client = client
        self.user = current_user(client)

    @db_errors
    def create_profile(self, name: str, phone: str, address: str | None = None) -> dict:
        """C — 가입 직후 프로필 생성. id 는 로그인 사용자 id 로 자동, member_type 은 DB 기본값(buyer)."""
        rows = (
            self.client.table("members")
            .insert({"id": self.user.id, "name": name, "phone": phone, "address": address})
            .execute()
            .data
        )
        return first_or_error(rows, "회원 생성")

    @db_errors
    def get_me(self) -> dict:
        """R — 내 프로필. RLS 가 본인 행만 보여 주지만 .eq 로 의도를 코드에도 남긴다 (응답 크기 절감 겸)."""
        rows = (
            self.client.table("members")
            .select(COLUMNS)
            .eq("id", self.user.id)
            .is_("deleted_at", "null")
            .execute()
            .data
        )
        return first_or_error(rows, "회원 조회")

    @db_errors
    def update_me(self, **fields) -> dict:
        """U — 내 프로필 수정."""
        rows = self.client.table("members").update(fields).eq("id", self.user.id).execute().data
        return first_or_error(rows, "회원 수정")

    @db_errors
    def withdraw(self) -> dict:
        """D — 탈퇴 = 소프트 삭제. 주문 이력(FK)을 보존하려면 물리 삭제할 수 없다."""
        now = datetime.now(timezone.utc).isoformat()
        rows = self.client.table("members").update({"deleted_at": now}).eq("id", self.user.id).execute().data
        return first_or_error(rows, "회원 탈퇴")
