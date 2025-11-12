-- =========================
-- Customers
-- =========================
CREATE TABLE IF NOT EXISTS public.customers (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL,
  name_key text NOT NULL UNIQUE,
  address text,
  city text,
  state text,
  zip text,
  lat DOUBLE PRECISION,
  lon DOUBLE PRECISION
);

-- =========================
-- Routes
-- =========================
CREATE TABLE IF NOT EXISTS public.routes (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  route_date TIMESTAMP NOT NULL,
  vehicle_index BIGINT NOT NULL,
  route_name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- =========================
-- Stops
-- =========================
CREATE TABLE IF NOT EXISTS public.stops (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  route_id BIGINT NOT NULL REFERENCES public.routes(id) ON DELETE CASCADE,
  customer_id BIGINT NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
  sequence BIGINT NOT NULL,
  notes TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);