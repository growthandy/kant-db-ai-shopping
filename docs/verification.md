# 검증 기록 — 2026-11-16

로컬 Supabase 스택(`supabase start`, CLI 2.109.1, PostgreSQL 17)에서 실행했습니다. 클라우드 프로젝트에서도 같은 순서로 재현됩니다.

## 환경

| 항목 | 값 |
|---|---|
| Python | 3.13 (uv) · supabase 2.34.1 · python-dotenv |
| API | `http://127.0.0.1:55321` (Publishable 키만 사용, service_role 미사용) |
| 계정 | `seller1@` · `buyer1@` · `buyer2@example.com` — Auth 가입(이메일 확인 OFF) |

## 절차와 결과

| 단계 | 명령 | 결과 | 로그 |
|---|---|---|---|
| 스키마 | `sql/01_schema.sql` | DROP → CREATE 4테이블 · 인덱스 3 · 트리거 3, 오류 0 | `logs/01_schema.log` |
| 변경 | `sql/02_alter_drop.sql` | ADD COLUMN · ADD CONSTRAINT · SET DEFAULT · DROP COLUMN 확인 | `logs/02_alter_drop.log` |
| 권한 | `sql/03_rls.sql` | RLS 4테이블 · 정책 9개 · 테이블/열 GRANT | `logs/03_rls.log` |
| RPC | `sql/04_functions.sql` | `create_order` · `cancel_order` (SECURITY DEFINER), anon 실행 권한 회수 | `logs/04_functions.log` |
| 시드 | `sql/05_seed.sql` | 회원 3 · 상품 3 | `logs/05_seed.log` |
| DML | `sql/06_dml_verify.sql` | INSERT 3→4 · UPDATE 후 `trigger_worked = t` · DELETE 후 0 · 제약 위반 5건 모두 ERROR, 데이터 변화 없음 | `logs/06_dml_verify.log` |
| 트랜잭션 | `sql/07_transaction_test.sql` | [A] COMMIT 후 키보드 재고 10→8, 총액 240000 · [B] ROLLBACK 후 가격 원복 · [C] `products_stock_chk` 위반 → `TX-C-0001` 0건, 재고 3 유지 · [D] FK RESTRICT 로 삭제 거절 | `logs/07_transaction_test.log` |
| SDK | `uv run main.py` | 24단계 전부 통과, 마지막 줄 `모든 검증 통과 ✅` (exit 0) | `logs/main.log` |

`main.py` 의 거절 9건은 모두 의도한 원인으로 거절됐습니다.

| 시도 | 거절 사유 |
|---|---|
| 구매자가 `member_type` 을 seller 로 수정 | 42501 열 GRANT |
| 전화번호 형식 위반 | 23514 `members_phone_chk` |
| 구매자가 상품 등록 | 42501 RLS `products_insert_seller` |
| 음수 가격 | 23514 `products_price_chk` |
| 정상 1개 + 재고 초과 1개 주문 | P0001 → 주문 수·재고 그대로 (롤백) |
| buyer2 가 buyer1 주문 조회 · 취소 · 상품 수정 | RLS 로 0행 / RPC 거절 |
| `total_price` 직접 수정 | 42501 열 GRANT |

## 설계 문서 대비 수정 2건

1. **`shop/product_service.py`** — `ProductService.list` 메서드가 클래스 본문에서 내장 `list` 를 가려, 그 뒤 메서드의 반환 타입 `list[dict]` 가 import 시점에 `TypeError: 'function' object is not subscriptable` 로 실패했다. `from __future__ import annotations` 로 주석 평가를 미뤄 해결.
2. **`sql/03_rls.sql`** — 최신 Supabase 는 `public` 에 새로 만든 테이블에 `anon`·`authenticated` 의 SELECT/INSERT/UPDATE/DELETE 권한을 자동으로 주지 않는다 (`\dp` 실측: `authenticated=Dxtm`). 그래서 첫 조회가 `permission denied for table members` (42501) 로 실패했다. 필요한 테이블 권한만 명시 GRANT 하는 4줄을 추가했다. 예전 프로젝트처럼 기본 권한이 있는 환경에서도 무해하다.

## 다시 돌리기

```bash
supabase start
# .env 에 supabase status 의 API_URL · PUBLISHABLE_KEY
for f in sql/0{1,2,3,4,5}_*.sql; do docker exec -i supabase_db_db-ai-shopping psql -U postgres -d postgres -v ON_ERROR_STOP=1 < "$f"; done
uv run main.py
```
