-- Money tracker schema (Postgres / Supabase)

create table if not exists users (
    id          uuid primary key default gen_random_uuid(),
    telegram_id bigint unique,
    name        text,
    created_at  timestamptz default now()
);

create table if not exists categories (
    id      uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    name    text not null,
    emoji   text,
    unique (user_id, name)
);

create table if not exists transactions (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references users(id) on delete cascade,
    amount      numeric(14,2) not null check (amount > 0),
    type        text not null check (type in ('expense', 'income')),
    category_id uuid references categories(id) on delete set null,
    note        text,
    image_url   text,
    occurred_at date not null default current_date,
    created_at  timestamptz default now()
);

create index if not exists idx_tx_user_date on transactions (user_id, occurred_at desc);
create index if not exists idx_tx_user_category on transactions (user_id, category_id);

insert into categories (user_id, name, emoji)
select u.id, c.name, c.emoji
from users u
cross join (values
    ('Ăn uống', '🍜'),
    ('Di chuyển', '🚗'),
    ('Mua sắm', '🛍️'),
    ('Hóa đơn', '🧾'),
    ('Giải trí', '🎮'),
    ('Sức khỏe', '💊'),
    ('Giáo dục', '📚'),
    ('Khác', '❓'),
    ('Lương', '💰'),
    ('Thưởng', '🎁')
) as c(name, emoji)
where not exists (
    select 1 from categories cat where cat.user_id = u.id and cat.name = c.name
);
