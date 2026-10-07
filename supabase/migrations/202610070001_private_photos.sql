begin;

create table public.photo_stations (
  id text primary key,
  version bigint not null default 0,
  state jsonb not null
);
create table public.photo_objects (
  path text primary key,
  expires_at timestamptz not null default now() + interval '10 minutes'
);
create index photo_objects_expiry on public.photo_objects(expires_at);
create table public.photo_rate_limits (
  key text primary key,
  count integer not null,
  expires_at timestamptz not null
);
alter table public.photo_stations enable row level security;
alter table public.photo_objects enable row level security;
alter table public.photo_rate_limits enable row level security;
revoke all on public.photo_stations, public.photo_objects, public.photo_rate_limits from anon, authenticated;
grant all on public.photo_stations, public.photo_objects, public.photo_rate_limits to service_role;

-- Commit a station transition and object lifetime changes together. Concurrent
-- heartbeat/start/delete requests must never overwrite one another.
create function public.photo_commit(station_id text, expected_version bigint,
  next_state jsonb, remove_paths text[], live_path text, live_expiry timestamptz)
returns boolean language plpgsql set search_path = '' as $$
begin
  update public.photo_stations set state=next_state, version=version+1
    where id=station_id and version=expected_version;
  if not found then return false; end if;
  update public.photo_objects set expires_at=now() where path=any(remove_paths);
  if live_path is not null then
    update public.photo_objects set expires_at=live_expiry where path=live_path;
    if not found then raise exception 'Missing staged image'; end if;
  end if;
  return true;
end $$;
create function public.photo_rate_limit(rate_key text, seconds integer)
returns integer language plpgsql set search_path = '' as $$
declare n integer;
begin
  insert into public.photo_rate_limits as r (key,count,expires_at)
  values(rate_key,1,now()+make_interval(secs=>seconds))
  on conflict(key) do update set
    count=case when r.expires_at<=now() then 1 else r.count+1 end,
    expires_at=case when r.expires_at<=now() then now()+make_interval(secs=>seconds) else r.expires_at end
  returning count into n;
  return n;
end $$;
revoke all on function public.photo_commit(text,bigint,jsonb,text[],text,timestamptz) from public, anon, authenticated;
revoke all on function public.photo_rate_limit(text,integer) from public, anon, authenticated;
grant execute on function public.photo_commit(text,bigint,jsonb,text[],text,timestamptz) to service_role;
grant execute on function public.photo_rate_limit(text,integer) to service_role;

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('alien-photos','alien-photos',false,716800,array['image/jpeg']);

commit;
