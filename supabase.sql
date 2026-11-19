-- 1. ВПИШИ СВОЙ EMAIL АДМИНА (тот, с которым будешь входить в админку) и только потом жми Run
create or replace function is_admin() returns boolean language sql stable as $$
  select coalesce(auth.jwt() ->> 'email','') = 'splyxzzzz@gmail.com'
$$;

-- 2. Таблицы
create table products(
  id bigint generated always as identity primary key,
  cat text not null default 'Разное',
  name text not null,
  sub text not null default '',
  price int not null check (price >= 0),
  stock int not null default 0 check (stock >= 0),
  emoji text not null default '📦',
  img text not null default '',
  created_at timestamptz default now()
);
create table orders(
  id bigint generated always as identity primary key,
  created_at timestamptz default now(),
  tg_id bigint, tg_username text,
  name text, phone text, addr text, note text,
  items jsonb not null,
  total int not null,
  status text not null default 'new' check (status in ('new','done','canceled'))
);

-- 3. Права: товары читают все, менять может только админ, заказы видит только админ
alter table products enable row level security;
alter table orders enable row level security;
create policy "read products" on products for select using (true);
create policy "admin products" on products for all using (is_admin()) with check (is_admin());
create policy "admin orders" on orders for all using (is_admin()) with check (is_admin());

-- 4. Фото товаров
insert into storage.buckets (id, name, public) values ('products', 'products', true) on conflict (id) do nothing;
create policy "products read" on storage.objects for select using (bucket_id = 'products');
create policy "products insert" on storage.objects for insert with check (bucket_id = 'products' and is_admin());
create policy "products delete" on storage.objects for delete using (bucket_id = 'products' and is_admin());

-- 5. Оформление заказа: цену и остаток проверяет и списывает сама база
create or replace function create_order(p_items jsonb, p_name text, p_phone text, p_addr text,
                                        p_note text, p_tg_id bigint, p_tg_username text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare it jsonb; pr products%rowtype; q int; total int := 0; lines jsonb := '[]'; oid bigint;
begin
  if jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then raise exception 'Корзина пуста'; end if;
  for it in select value from jsonb_array_elements(p_items) loop
    q := (it->>'qty')::int;
    if q < 1 or q > 50 then raise exception 'Неверное количество'; end if;
    select * into pr from products where id = (it->>'id')::bigint for update;
    if not found then raise exception 'Товар не найден'; end if;
    if pr.stock < q then raise exception 'Нет в наличии: %', pr.name; end if;
    update products set stock = stock - q where id = pr.id;
    total := total + pr.price * q;
    lines := lines || jsonb_build_object('id', pr.id, 'name', pr.name, 'cat', pr.cat, 'qty', q, 'price', pr.price);
  end loop;
  insert into orders(tg_id, tg_username, name, phone, addr, note, items, total)
  values (p_tg_id, p_tg_username, left(p_name,100), left(p_phone,40), left(p_addr,300), left(p_note,300), lines, total)
  returning id into oid;
  return jsonb_build_object('id', oid, 'total', total, 'items', lines);
end $$;
grant execute on function create_order to anon, authenticated;

-- 6. Отмена заказа возвращает товар на склад (только админ)
create or replace function cancel_order(oid bigint) returns void
language plpgsql security definer set search_path = public as $$
declare o orders%rowtype; it jsonb;
begin
  if not is_admin() then raise exception 'forbidden'; end if;
  select * into o from orders where id = oid for update;
  if not found or o.status = 'canceled' then return; end if;
  for it in select value from jsonb_array_elements(o.items) loop
    update products set stock = stock + (it->>'qty')::int where id = (it->>'id')::bigint;
  end loop;
  update orders set status = 'canceled' where id = oid;
end $$;
grant execute on function cancel_order to authenticated;

-- 7. Демо-товары (можно удалить потом в админке)
insert into products(cat, name, sub, price, stock, emoji) values
 ('Наушники','AirPods Pro 2','Шумоподавление · USB-C',115000,15,'🎧'),
 ('Наушники','Sony WH-1000XM5','Полноразмерные · чёрные',165000,8,'🎧'),
 ('Наушники','Marshall Major IV','До 80 часов работы',75000,12,'🎧'),
 ('Наушники','Samsung Galaxy Buds2 Pro','Вакуумные · графит',85000,18,'🎧'),
 ('Наушники','JBL Tune 510BT','Накладные · синие',24000,25,'🎧'),
 ('Наушники','HyperX Cloud II','Игровые · 7.1 звук',48000,10,'🎧'),
 ('Наушники','Logitech G Pro X','Проводные · микрофон Blue',65000,7,'🎧'),
 ('Наушники','Nothing Ear (2)','Прозрачный кейс',72000,9,'🎧'),
 ('Наушники','Sennheiser HD 450BT','Складные · белый',68000,6,'🎧'),
 ('Наушники','Xiaomi Redmi Buds 5','Бюджетные · ANC',19000,30,'🎧'),

 ('Телефоны','iPhone 15 Pro','256 ГБ · натуральный титан',580000,5,'📱'),
 ('Телефоны','iPhone 15','128 ГБ · чёрный',420000,11,'📱'),
 ('Телефоны','Samsung Galaxy S24 Ultra','512 ГБ · стилус S-Pen',620000,4,'📱'),
 ('Телефоны','Samsung Galaxy A55','256 ГБ · тёмно-синий',210000,14,'📱'),
 ('Телефоны','Google Pixel 8 Pro','128 ГБ · обсидиан',450000,6,'📱'),
 ('Телефоны','Xiaomi 14','512 ГБ · камера Leica',430000,8,'📱'),
 ('Телефоны','POCO X6 Pro','512 ГБ · жёлтый',165000,19,'📱'),
 ('Телефоны','Nothing Phone (2)','256 ГБ · подсветка Glyph',310000,7,'📱'),
 ('Телефоны','OnePlus 12','512 ГБ · зелёный',440000,5,'📱'),
 ('Телефоны','Realme 12 Pro+','256 ГБ · бежевый',185000,13,'📱'),

 ('Мышки','Logitech G Pro X Superlight','Беспроводная · 63 г',72000,14,'🖱️'),
 ('Мышки','Logitech MX Master 3S','Для работы · тихие клики',58000,10,'🖱️'),
 ('Мышки','Razer DeathAdder V3 Pro','Эргономичная · чёрная',79000,8,'🖱️'),
 ('Мышки','Razer Viper V2 Pro','Ультралёгкая · 58 г',74000,9,'🖱️'),
 ('Мышки','Apple Magic Mouse','Сенсорная панель · белая',45000,16,'🖱️'),
 ('Мышки','Logitech G102 Lightsync','Проводная · RGB подсветка',13500,35,'🖱️'),
 ('Мышки','SteelSeries Aerox 3','Перфорированный корпус',39000,11,'🖱️'),
 ('Мышки','HyperX Pulsefire Haste','Сотовый дизайн · 59 г',26000,20,'🖱️'),
 ('Мышки','Keychron M3','Беспроводная · 4K Гц',34000,12,'🖱️'),
 ('Мышки','Xiaomi Mi Dual Mode','Офисная · бесшумная',9500,28,'🖱️'),

 ('Ноутбуки','MacBook Air 13 M2','8/256 ГБ · тёмная ночь',540000,7,'💻'),
 ('Ноутбуки','MacBook Pro 14 M3 Pro','18/512 ГБ · чёрный космос',1050000,3,'💻'),
 ('Ноутбуки','ASUS ROG Zephyrus G14','RTX 4060 · 16/1000 ГБ',790000,4,'💻'),
 ('Ноутбуки','Lenovo Legion 5 Pro','RTX 4070 · 32/1000 ГБ',880000,5,'💻'),
 ('Ноутбуки','ASUS Zenbook 14 OLED','Core Ultra 7 · 16/512 ГБ',510000,8,'💻'),
 ('Ноутбуки','HP Pavilion 15','Ryzen 5 · 16/512 ГБ',310000,12,'💻'),
 ('Ноутбуки','Acer Nitro V 15','RTX 4050 · 16/512 ГБ',420000,9,'💻'),
 ('Ноутбуки','Huawei MateBook D 16','Core i5 · 16/512 ГБ',360000,10,'💻'),
 ('Ноутбуки','Dell XPS 13','Сенсорный экран · 16/512 ГБ',690000,4,'💻'),
 ('Ноутбуки','MSI Katana 15','RTX 4060 · 16/1000 ГБ',560000,6,'💻');