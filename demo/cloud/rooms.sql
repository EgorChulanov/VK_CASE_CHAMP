-- The service role is the only caller allowed to access rooms. An invitation is hashed at the edge.
create table public.jury_rooms (
  room text primary key check (length(room) = 64),
  version integer not null default 1,
  state jsonb not null check (octet_length(state::text) <= 10485760),
  touched timestamptz not null default now()
);
alter table public.jury_rooms enable row level security;
revoke all on public.jury_rooms from public, anon, authenticated;
grant select, insert, update, delete on public.jury_rooms to service_role;
create index jury_rooms_expiry on public.jury_rooms(touched);
create function public.jury_open_room(p_room text, p_seed jsonb) returns void
language plpgsql security invoker set search_path = '' as $$
begin
  if exists (select 1 from public.jury_rooms where room = p_room) then return; end if;
  perform pg_advisory_xact_lock(719026);
  delete from public.jury_rooms where touched < now() - interval '30 days';
  if (select count(*) from public.jury_rooms) >= 2000 then raise exception 'capacity'; end if;
  insert into public.jury_rooms (room,state) values (p_room,p_seed) on conflict do nothing;
end
$$;
revoke all on function public.jury_open_room(text,jsonb) from public, anon, authenticated;
grant execute on function public.jury_open_room(text,jsonb) to service_role;
