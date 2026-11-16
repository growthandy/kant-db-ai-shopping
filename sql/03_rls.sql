alter table public.members     enable row level security;
alter table public.products    enable row level security;
alter table public.orders      enable row level security;
alter table public.order_items enable row level security;

-- 신규 Supabase 프로젝트는 public 테이블에 anon/authenticated 권한을 자동으로 주지 않는다 → 필요한 것만 명시
grant select, insert on public.members to authenticated;
grant select, insert, update, delete on public.products to authenticated;
grant select on public.orders to authenticated;
grant select on public.order_items to authenticated;

create policy members_select_own on public.members
  for select to authenticated
  using (id = (select auth.uid()));

create policy members_insert_own on public.members
  for insert to authenticated
  with check (id = (select auth.uid()) and member_type = 'buyer');

create policy members_update_own on public.members
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

revoke update on public.members from authenticated, anon;
grant update (name, phone, zip_code, address, address_detail, marketing_agreed, deleted_at)
  on public.members to authenticated;

create policy products_select_active on public.products
  for select to authenticated
  using (deleted_at is null or seller_id = (select auth.uid()));

create policy products_insert_seller on public.products
  for insert to authenticated
  with check (
    seller_id = (select auth.uid())
    and exists (
      select 1 from public.members m
      where m.id = (select auth.uid()) and m.member_type = 'seller' and m.deleted_at is null
    )
  );

create policy products_update_seller on public.products
  for update to authenticated
  using (seller_id = (select auth.uid()))
  with check (seller_id = (select auth.uid()));

create policy products_delete_seller on public.products
  for delete to authenticated
  using (seller_id = (select auth.uid()));

create policy orders_select_own on public.orders
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy orders_update_own_before_payment on public.orders
  for update to authenticated
  using (user_id = (select auth.uid()) and order_status in ('READY', 'ORDER'))
  with check (user_id = (select auth.uid()));

revoke update on public.orders from authenticated, anon;
grant update (receiver_name, receiver_phone, address, delivery_memo) on public.orders to authenticated;

create policy order_items_select_own on public.order_items
  for select to authenticated
  using (
    exists (
      select 1 from public.orders o
      where o.id = order_items.order_id and o.user_id = (select auth.uid())
    )
  );

select tablename, policyname, cmd, roles, qual as using_expr, with_check
from pg_policies
where schemaname = 'public'
order by tablename, cmd;
