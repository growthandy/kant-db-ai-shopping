select count(*) as before_count from public.products;

insert into public.products (seller_id, name, price, stock)
select id, 'USB 허브', 25000, 15 from public.members where member_type = 'seller'
returning id, name, price, stock, created_at;

select count(*) as after_count from public.products;
select name, description from public.products where name = 'USB 허브';

select id, name, price, updated_at from public.products where name = 'USB 허브';

update public.products
   set price = 22000
 where name = 'USB 허브'
returning name, price, updated_at;

select name, price, created_at, updated_at,
       updated_at > created_at as trigger_worked
from public.products where name = 'USB 허브';

select id, name from public.products where name = 'USB 허브';
delete from public.products where name = 'USB 허브' returning id, name;
select count(*) as should_be_zero from public.products where name = 'USB 허브';

insert into public.products (seller_id, name, price)
select id, null, 1000 from public.members where member_type = 'seller';

insert into public.products (seller_id, name, price)
select id, '음수 상품', -500 from public.members where member_type = 'seller';

insert into public.products (seller_id, name, price)
values ('00000000-0000-0000-0000-000000000000', '유령 상품', 1000);

insert into public.products (seller_id, name, price)
select id, '무선 키보드', 1 from public.members where member_type = 'seller';

update public.members set member_type = 'admin' where name = '이구매';

select count(*) from public.products where name in ('음수 상품', '유령 상품');
select member_type from public.members where name = '이구매';

select tc.table_name,
       tc.constraint_name,
       tc.constraint_type,
       kcu.column_name,
       ccu.table_schema || '.' || ccu.table_name || '.' || ccu.column_name as references_to
from information_schema.table_constraints tc
left join information_schema.key_column_usage kcu
       on kcu.constraint_name = tc.constraint_name and kcu.table_schema = tc.table_schema
left join information_schema.constraint_column_usage ccu
       on ccu.constraint_name = tc.constraint_name and tc.constraint_type = 'FOREIGN KEY'
where tc.table_schema = 'public'
  and tc.table_name in ('members', 'products', 'orders', 'order_items')
  and tc.constraint_type in ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK')
  and tc.constraint_name not like '%_not_null'
order by tc.table_name, tc.constraint_type, tc.constraint_name;
