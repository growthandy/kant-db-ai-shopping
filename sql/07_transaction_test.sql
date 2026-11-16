select name, stock from public.products order by name;
select count(*) as order_count from public.orders;

begin;

  insert into public.orders (order_no, user_id, receiver_name, receiver_phone, address)
  select 'TX-A-0001', m.id, '이구매', '010-2000-0002', '서울시 중구 세종대로 2'
  from public.members m join auth.users u on u.id = m.id
  where u.email = 'buyer1@example.com';

  insert into public.order_items (order_id, product_id, item_name, item_price, quantity)
  select o.id, p.id, p.name, p.price, 2
  from public.orders o, public.products p
  where o.order_no = 'TX-A-0001' and p.name = '무선 키보드';

  update public.products set stock = stock - 2 where name = '무선 키보드';

  update public.orders o
     set total_price = (select sum(item_price * quantity) from public.order_items where order_id = o.id)
   where o.order_no = 'TX-A-0001';

commit;

select o.order_no, o.total_price, oi.item_name, oi.quantity, p.stock
from public.orders o
join public.order_items oi on oi.order_id = o.id
join public.products p on p.id = oi.product_id
where o.order_no = 'TX-A-0001';

begin;
  update public.products set price = 0;
  select name, price from public.products order by name;
rollback;

select name, price from public.products order by name;

begin;

  insert into public.orders (order_no, user_id, receiver_name, receiver_phone, address)
  select 'TX-C-0001', m.id, '박구매', '010-3000-0003', '부산시 해운대구 센텀로 3'
  from public.members m join auth.users u on u.id = m.id
  where u.email = 'buyer2@example.com';

  insert into public.order_items (order_id, product_id, item_name, item_price, quantity)
  select o.id, p.id, p.name, p.price, 5
  from public.orders o, public.products p
  where o.order_no = 'TX-C-0001' and p.name = '모니터 받침대';

  update public.products set stock = stock - 5 where name = '모니터 받침대';

commit;

rollback;

select count(*) as should_be_zero from public.orders where order_no = 'TX-C-0001';
select name, stock as should_be_3 from public.products where name = '모니터 받침대';

delete from public.products where name = '무선 키보드';
