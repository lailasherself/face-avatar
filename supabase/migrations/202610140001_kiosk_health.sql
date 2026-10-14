-- Installation health heartbeats from the kiosk (scripts/kiosk_health.py).
-- The kiosk inserts one row per minute with the anon key; the GitHub monitor
-- workflow reads the latest row. Rows older than seven days are purged on insert.
create table if not exists public.kiosk_health (
  id bigint generated always as identity primary key,
  station text not null check (char_length(station) between 1 and 64),
  created_at timestamptz not null default now(),
  ok boolean not null,
  summary text not null default '' check (char_length(summary) <= 500),
  checks jsonb not null default '{}'::jsonb check (pg_column_size(checks) <= 16384),
  actions jsonb not null default '[]'::jsonb check (pg_column_size(actions) <= 4096),
  version text check (char_length(version) <= 64)
);
create index if not exists kiosk_health_station_created_idx on public.kiosk_health (station, created_at desc);

alter table public.kiosk_health enable row level security;
drop policy if exists kiosk_health_insert on public.kiosk_health;
create policy kiosk_health_insert on public.kiosk_health for insert to anon, authenticated with check (true);
drop policy if exists kiosk_health_read on public.kiosk_health;
create policy kiosk_health_read on public.kiosk_health for select to anon, authenticated using (true);

create or replace function public.kiosk_health_purge() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  delete from public.kiosk_health where created_at < now() - interval '7 days';
  return null;
end $$;
drop trigger if exists kiosk_health_purge_trigger on public.kiosk_health;
create trigger kiosk_health_purge_trigger after insert on public.kiosk_health
  for each statement execute function public.kiosk_health_purge();

-- A single rate guard: at most one row per station per 20 seconds.
create or replace function public.kiosk_health_rate_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.kiosk_health where station = new.station and created_at > now() - interval '20 seconds') then
    raise exception 'kiosk_health: too many heartbeats for %', new.station using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists kiosk_health_rate_guard_trigger on public.kiosk_health;
create trigger kiosk_health_rate_guard_trigger before insert on public.kiosk_health
  for each row execute function public.kiosk_health_rate_guard();
