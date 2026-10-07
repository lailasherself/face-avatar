begin;

alter table public.photo_stations add column expires_at timestamptz;
create index photo_stations_expiry on public.photo_stations(expires_at);

-- Only the server can allocate stations. Serialize allocation to enforce the cap.
create function public.photo_provision(station_id text, initial_state jsonb)
returns boolean language plpgsql set search_path = '' as $$
begin
  if station_id !~ '^test-[a-f0-9]{32}$' or initial_state->>'id' <> station_id then
    raise exception 'Invalid test station';
  end if;
  perform pg_advisory_xact_lock(73190427);
  if exists(select 1 from public.photo_stations where id=station_id and expires_at>now()) then
    return true;
  end if;
  if (select count(*) from public.photo_stations where expires_at>now()) >= 64 then
    return false;
  end if;
  insert into public.photo_stations(id,state,expires_at)
    values(station_id,initial_state,now()+interval '48 hours')
    on conflict(id) do update set state=excluded.state, version=photo_stations.version+1, expires_at=excluded.expires_at;
  return true;
end $$;
revoke all on function public.photo_provision(text,jsonb) from public, anon, authenticated;
grant execute on function public.photo_provision(text,jsonb) to service_role;

create or replace function public.photo_commit(station_id text, expected_version bigint,
  next_state jsonb, remove_paths text[], live_path text, live_expiry timestamptz)
returns boolean language plpgsql set search_path = '' as $$
begin
  update public.photo_stations set state=next_state, version=version+1,
    -- Only an authenticated camera heartbeat advances operatorAt. Keep station
    -- metadata longer than every photo's 24-hour lifetime. Fixed station is null.
    expires_at=case when expires_at is null then null else greatest(expires_at,
      to_timestamp((next_state->>'operatorAt')::double precision/1000)+interval '48 hours') end
    where id=station_id and version=expected_version and (expires_at is null or expires_at>now());
  if not found then return false; end if;
  update public.photo_objects set expires_at=now() where path=any(remove_paths);
  if live_path is not null then
    update public.photo_objects set expires_at=live_expiry where path=live_path;
    if not found then raise exception 'Missing staged image'; end if;
  end if;
  return true;
end $$;

commit;
