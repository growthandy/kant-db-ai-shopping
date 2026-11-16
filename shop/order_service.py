"""주문(orders + order_items) CRUD."""

from supabase import Client

from shop.client import current_user
from shop.errors import db_errors, first_or_error

COLUMNS = (
    "id, order_no, total_price, order_status, receiver_name, receiver_phone, address, delivery_memo, created_at, "
    "order_items(product_id, item_name, item_price, quantity)"
)

class OrderService:
    def __init__(self, client: Client):
        self.client = client
        self.user = current_user(client)

    @db_errors
    def create(
        self,
        items: list[dict],
        receiver_name: str,
        receiver_phone: str,
        address: str,
        delivery_memo: str | None = None,
    ) -> dict:
        """C — create_order RPC. 보내는 것은 product_id·quantity 뿐, 가격·주문자는 DB 가 정한다."""
        params = {
            "p_receiver_name": receiver_name,
            "p_receiver_phone": receiver_phone,
            "p_address": address,
            "p_delivery_memo": delivery_memo,
            "p_items": items,
        }
        return self.client.rpc("create_order", params).execute().data

    @db_errors
    def list_mine(self) -> list[dict]:
        """R(목록) — 내 주문, 최신순. RLS 가 이미 본인 것만 주지만 .eq 를 남긴다."""
        return (
            self.client.table("orders")
            .select(COLUMNS)
            .eq("user_id", self.user.id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    @db_errors
    def get(self, order_id: str) -> dict:
        """R(단건) — 남의 주문 id 를 넣으면 RLS 때문에 0행 → '없거나 권한 없음'."""
        rows = self.client.table("orders").select(COLUMNS).eq("id", order_id).execute().data
        return first_or_error(rows, "주문 조회")

    @db_errors
    def update_shipping(self, order_id: str, **fields) -> dict:
        """U — 결제 전 주문의 수령인·주소·메모만. 다른 열(total_price 등)은 열 GRANT 가 42501 로 막는다."""
        rows = self.client.table("orders").update(fields).eq("id", order_id).execute().data
        return first_or_error(rows, "주문 수정")

    @db_errors
    def cancel(self, order_id: str) -> dict:
        """D — cancel_order RPC: 재고 복구 + 주문 삭제(주문상품 CASCADE)를 한 트랜잭션으로."""
        return self.client.rpc("cancel_order", {"p_order_id": order_id}).execute().data
