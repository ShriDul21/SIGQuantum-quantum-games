-- Run once in the Supabase SQL Editor for this project.
create table public.quantum_scores (
  id uuid primary key,
  nickname text not null check (char_length(btrim(nickname)) between 1 and 24),
  score integer not null check (score >= 0),
  attempts integer not null check (attempts between 1 and 172 and score <= attempts),
  accuracy numeric generated always as (score::numeric / attempts) stored,
  created_at timestamptz not null default now()
);

create index quantum_scores_ranking_idx
  on public.quantum_scores (score desc, accuracy desc, created_at asc, id asc);

-- No public policies: all reads and writes go through the Vercel API.
alter table public.quantum_scores enable row level security;
revoke all on table public.quantum_scores from anon, authenticated;
grant select, insert on table public.quantum_scores to service_role;
