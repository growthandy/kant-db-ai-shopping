alter table public.members
  add column marketing_agreed boolean not null default false;

alter table public.products
  add constraint products_seller_name_uq unique (seller_id, name);

alter table public.products
  alter column description set default '상품 설명을 입력해 주세요.';

alter table public.orders add column coupon_code text;
alter table public.orders drop column coupon_code;

select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
  and table_name in ('members', 'products', 'orders')
  and column_name in ('marketing_agreed', 'description', 'coupon_code')
order by table_name, column_name;
