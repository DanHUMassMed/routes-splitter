## Create Table Statement for Supabase
```sql
create extension if not exists postgis;

create table if not exists public.customers (
  id bigint generated always as identity primary key,
  name text not null,
  name_key text not null unique,
  address text,
  city text,
  state text,
  zip text,
  location geography(point, 4326)
);

create index if not exists customers_location_idx on public.customers using gist (location);
```

```sql
create table if not exists public.routes (
  id bigint generated always as identity primary key,
  route_date TIMESTAMP not null,
  driver_index bigint not null,
  route_name text not null,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

```


```sql
create table if not exists public.stops (
  id bigint generated always as identity primary key,
  route_id bigint not null,
  customer_id bigint not null,
  order_id bigint not null,
  notes text not null,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

```