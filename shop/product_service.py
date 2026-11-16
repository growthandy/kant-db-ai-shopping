"""상품(products) CRUD — 판매자가 등록·수정·삭제하고, 로그인 사용자 누구나 조회한다."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from shop.client import current_user
from shop.errors import ServiceError, db_errors, first_or_error

COLUMNS = "id, seller_id, name, description, price, stock, created_at, updated_at, deleted_at"

class ProductService:
    def __init__(self, client: Client):
        self.client = client
        self.user = current_user(client)

    @db_errors
    def create(self, name: str, price: int, stock: int, description: str | None = None) -> dict:
        """C — seller_id 는 로그인 사용자로 자동. 구매자가 부르면 RLS(products_insert_seller)가 42501 로 거절."""
        payload = {"seller_id": self.user.id, "name": name, "price": price, "stock": stock}
        if description is not None:
            payload["description"] = description
        rows = self.client.table("products").insert(payload).execute().data
        return first_or_error(rows, "상품 생성")

    @db_errors
    def list(self, keyword: str | None = None) -> list[dict]:
        """R(목록) — 판매 중인 상품, 가격 높은 순. keyword 는 대소문자 무시 부분 일치."""
        query = self.client.table("products").select(COLUMNS).is_("deleted_at", "null")
        if keyword:
            query = query.ilike("name", f"%{keyword}%")
        return query.order("price", desc=True).execute().data

    @db_errors
    def get(self, product_id: str) -> dict:
        """R(단건) — 판매자는 판매 중지한 자기 상품도 볼 수 있다 (products_select_active 정책)."""
        rows = self.client.table("products").select(COLUMNS).eq("id", product_id).execute().data
        return first_or_error(rows, "상품 조회")

    @db_errors
    def update(self, product_id: str, **fields) -> dict:
        """U — .eq("id", ...) 는 절대 생략하지 않는다. 빠지면 내 상품 전부가 바뀐다 (WHERE 규율)."""
        rows = self.client.table("products").update(fields).eq("id", product_id).execute().data
        return first_or_error(rows, "상품 수정")

    def delete(self, product_id: str) -> dict:
        """D — 물리 삭제를 시도하고, 주문된 적 있는 상품(FK RESTRICT, 23503)이면 소프트 삭제로 전환."""
        try:
            rows = self._hard_delete(product_id)
            first_or_error(rows, "상품 삭제")
            return {"product_id": product_id, "mode": "hard"}
        except ServiceError as error:
            if error.code != "23503":
                raise
        now = datetime.now(timezone.utc).isoformat()
        self.update(product_id, deleted_at=now)
        return {"product_id": product_id, "mode": "soft", "reason": "주문 이력이 있어 판매 중지로 처리"}

    @db_errors
    def _hard_delete(self, product_id: str) -> list[dict]:
        return self.client.table("products").delete().eq("id", product_id).execute().data
