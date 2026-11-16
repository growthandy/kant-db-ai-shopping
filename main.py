"""uv run main.py — 회원·상품·주문 CRUD 와 RLS·트랜잭션을 단계별로 출력한다."""

import json
import os
import time

from postgrest.exceptions import APIError

from shop.client import login
from shop.errors import ServiceError
from shop.member_service import MemberService
from shop.order_service import OrderService
from shop.product_service import ProductService

PASSWORD = os.getenv("DEMO_PASSWORD", "")
SELLER, BUYER1, BUYER2 = "seller1@example.com", "buyer1@example.com", "buyer2@example.com"
SHIPPING = {"receiver_name": "이구매", "receiver_phone": "010-2000-0002", "address": "서울시 중구 세종대로 2"}

def show(title: str, data=None) -> None:
    print(f"\n=== {title}")
    if data is not None:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))

def expect_error(title: str, action) -> None:
    """실패해야 정상인 동작. 성공해 버리면 검증 실패로 멈춘다."""
    try:
        action()
    except (ServiceError, APIError) as error:
        print(f"\n=== {title} → 예상대로 거절\n    {error}")
        return
    raise AssertionError(f"{title}: 거절되어야 하는데 성공했습니다.")

def main() -> None:
    seller, buyer1, buyer2 = login(SELLER, PASSWORD), login(BUYER1, PASSWORD), login(BUYER2, PASSWORD)
    show("0. 로그인", {"seller": SELLER, "buyer1": BUYER1, "buyer2": BUYER2})

    members = MemberService(buyer1)
    before = members.get_me()
    after = members.update_me(phone="010-2000-9999", marketing_agreed=True)
    show("1-1. [회원 R·U] buyer1 수정 전/후", {"before": before, "after": after})
    assert after["phone"] == "010-2000-9999" and after["updated_at"] > before["updated_at"]
    expect_error("1-2. [회원 U] 구매자가 member_type 을 seller 로 바꾸기 (열 GRANT)",
                 lambda: members.update_me(member_type="seller"))
    expect_error("1-3. [회원 U] 전화번호 형식 위반 (CHECK)", lambda: members.update_me(phone="12345"))
    members.update_me(phone="010-2000-0002")

    products = ProductService(seller)
    stamp = time.strftime("%H%M%S")
    product = products.create(name=f"데모 키보드 {stamp}", price=120000, stock=5)
    show("2-1. [상품 C] 판매자가 등록", product)
    expect_error("2-2. [상품 C] 구매자가 상품 등록 (RLS products_insert_seller)",
                 lambda: ProductService(buyer1).create(name=f"불법 상품 {stamp}", price=1, stock=1))
    expect_error("2-3. [상품 C] 음수 가격 (CHECK products_price_chk)",
                 lambda: products.create(name=f"음수 {stamp}", price=-1, stock=1))
    updated = products.update(product["id"], price=99000)
    show("2-4. [상품 U] 가격 120000 → 99000", {"before": product["price"], "after": updated["price"]})
    assert updated["price"] == 99000
    show("2-5. [상품 R] 구매자가 보는 '데모' 검색 결과", ProductService(buyer1).list("데모"))

    orders = OrderService(buyer1)
    stock_before = products.get(product["id"])["stock"]
    order = orders.create(items=[{"product_id": product["id"], "quantity": 2}], **SHIPPING)
    stock_after = products.get(product["id"])["stock"]
    show("3-1. [주문 C] create_order RPC 응답", order)
    show("3-2. [주문 R] 주문 상세 (order_items 중첩)", orders.get(order["order_id"]))
    show("3-3. 재고 변화", {"before": stock_before, "after": stock_after})
    assert stock_after == stock_before - 2
    assert order["total_price"] == 99000 * 2

    count_before = len(orders.list_mine())
    expect_error("4-1. [트랜잭션] 정상 1개 + 재고 초과 1개 묶음 주문",
                 lambda: orders.create(items=[{"product_id": product["id"], "quantity": 1},
                                              {"product_id": product["id"], "quantity": 999}], **SHIPPING))
    count_after = len(orders.list_mine())
    stock_now = products.get(product["id"])["stock"]
    show("4-2. 롤백 검증 — 주문 수·재고가 그대로인가",
         {"orders": [count_before, count_after], "stock": [stock_after, stock_now]})
    assert count_after == count_before and stock_now == stock_after

    others = OrderService(buyer2)
    visible = [o["id"] for o in others.list_mine()]
    show("5-1. [RLS] buyer2 의 주문 목록에 buyer1 주문이 있는가", {"found": order["order_id"] in visible})
    assert order["order_id"] not in visible
    expect_error("5-2. [RLS] buyer2 가 buyer1 주문 단건 조회", lambda: others.get(order["order_id"]))
    expect_error("5-3. [RLS] buyer2 가 buyer1 주문 취소", lambda: others.cancel(order["order_id"]))
    expect_error("5-4. [RLS] buyer2 가 buyer1 상품 수정 (판매자 아님)",
                 lambda: ProductService(buyer2).update(product["id"], price=1))

    show("6-1. [주문 U] 배송 메모 수정",
         orders.update_shipping(order["order_id"], delivery_memo="문 앞에 놓아주세요"))
    expect_error("6-2. [주문 U] total_price 직접 수정 (열 GRANT)",
                 lambda: buyer1.table("orders").update({"total_price": 1}).eq("id", order["order_id"]).execute())

    extra = orders.create(items=[{"product_id": product["id"], "quantity": 1}], **SHIPPING)
    stock_mid = products.get(product["id"])["stock"]
    show("7-1. [주문 D] cancel_order RPC", orders.cancel(extra["order_id"]))
    stock_end = products.get(product["id"])["stock"]
    show("7-2. 재고 복구", {"주문 후": stock_mid, "취소 후": stock_end})
    assert stock_end == stock_mid + 1

    show("8-1. [상품 D] 주문된 상품 삭제 → FK RESTRICT → 소프트 삭제", products.delete(product["id"]))
    temp = products.create(name=f"임시 상품 {stamp}", price=1000, stock=1)
    show("8-2. [상품 D] 주문 없는 상품 삭제 → 물리 삭제", products.delete(temp["id"]))
    assert all(p["id"] != product["id"] for p in ProductService(buyer1).list())

    print("\n모든 검증 통과 ✅")

if __name__ == "__main__":
    main()
