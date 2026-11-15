# Quantum arithmetic

A minimal, 60-second game about applying quantum gates to single-qubit states.

Open `index.html` in a browser. Choose an answer with the mouse or keys **1–4**. Press **Enter** to start or play again.

Includes X, Y, Z, and H gates, computational and superposition states, and explicit phases. No runtime dependencies or build step.

## Leaderboard

An optional shared top-10 leaderboard stores rounds in Supabase. Finish a round, enter a nickname, and post your score. Rankings use correct answers, then accuracy, then earliest submission. Each round can be posted once; nicknames are not unique identities and repeat players can occupy multiple spots. Your personal best is still saved locally.

The browser calls `/api/scores`, a Vercel Function. Only that function has the Supabase secret key. The game still works if the leaderboard is offline or not configured. Opening `index.html` directly supports the game, but not shared scores.

## Set up Supabase

1. Create a project at [supabase.com](https://supabase.com/dashboard).
2. Open **SQL Editor → New query**, paste [`supabase/schema.sql`](supabase/schema.sql), and click **Run**. Run this initial schema only once. It creates `quantum_scores`, its ranking index, and enables Row Level Security. Do not add public read/write policies: the Vercel API handles database access.
3. Copy your **Project URL** from the project's **Connect** dialog (looks like `https://your-project-ref.supabase.co`).
4. Open **Settings → API Keys** and create/copy a **secret key** beginning with `sb_secret_`. This is a backend-only key, **not** the publishable key.

Never paste the secret key into `game.js`, `leaderboard.js`, HTML, GitHub, or chat. You don't need Supabase Auth, a browser Supabase client, a connection string, or a Vercel marketplace integration.

## Deploy to Vercel

1. Push this repository to GitHub.
2. In [Vercel](https://vercel.com/new), import the repository.
   Set the project's **Production Branch** to **`main`**, not `master` (the standalone Python poker branch).
3. Use these project settings:
   - **Framework Preset:** Other
   - **Root Directory:** `games/quantum-arithmetic`
   - **Build Command:** no command (if needed, enable Override and leave it empty)
   - **Output Directory:** `.` (relative to the game's Root Directory)
   - **Node.js:** 22.x (also set in `package.json`)

   The included `vercel.json` pins the framework, build command, and output directory. Root Directory and Production Branch are project settings you must set in Vercel; the config cannot select them.
4. Add these **Environment Variables** before deploying:

   | Name | Value |
   | --- | --- |
   | `SUPABASE_URL` | Your Supabase Project URL |
   | `SUPABASE_SECRET_KEY` | Your `sb_secret_...` key |

   Enable **Production**. Enable **Preview** too if you want leaderboard access on preview deployments; those deployments will share the same scores unless you use a separate Supabase project.
5. Click **Deploy**. Vercel serves the static files and automatically deploys `api/scores.js` at `/api/scores`.
6. Visit your deployed URL. The board should say "A clean slate". Finish a round and submit a nickname, then refresh to verify persistence.

For an existing deployment: set **Project → Settings → Build and Deployment → Root Directory** to `games/quantum-arithmetic`, keep Output Directory as `.`, and add both environment variables under **Settings → Environment Variables**. Then **Deployments → latest deployment → Redeploy** using the commit with the new folder layout. Environment variable changes apply to new deployments, not the currently running one. Changing the existing project's root preserves its project URL, domains, and configured environment variables.

Other games can be imported as separate Vercel projects from this same GitHub repository, each with its own Root Directory. This game's `/api/scores` remains at its deployment's `/api/scores`, not `/games/quantum-arithmetic/api/scores`. No frontend URL changes are needed.

### Local development with the API

Use Node.js 22 and the Vercel CLI. Run the CLI from the **repository root**, not this game folder. Link it to the quantum-arithmetic Vercel project whose Root Directory is `games/quantum-arithmetic`:

```sh
npx vercel link
```

Add `SUPABASE_URL` and `SUPABASE_SECRET_KEY` to that project's **Development** environment in Vercel as well; `vercel dev` uses the linked project's development variables. Alternatively, copy `games/quantum-arithmetic/.env.example` to `.env.local` at the repository root and fill it with your own values. Environment files and `.vercel/` are gitignored. Then run from the repository root:

```sh
npx vercel dev
```

Open the localhost URL it prints. A plain static file server won't run `/api/scores`.

### Troubleshooting

- **404 at the website homepage:** confirm the deployment uses the latest commit on `main`, Root Directory is `games/quantum-arithmetic`, Framework is Other, and Output Directory is `.`. There is no root-level website or `dist` folder. Deploy again after updating settings and open the new deployment's URL at `/`, not `/games/quantum-arithmetic/`.
- **"Leaderboard not configured yet":** check both Vercel environment variable names and their deployment environment, then redeploy.
- **"Leaderboard unavailable":** make sure the SQL ran in the same Supabase project as your URL/key, the project is active, the Data API is enabled for the `public` schema, and you used a secret—not publishable—key.
- **404 or HTML from `/api/scores`:** check the Vercel root directory and Framework Preset. Do not add a catch-all rewrite to `index.html`; it would hide the API route.
- **Scores work in production but not previews:** add the variables to Preview and redeploy that preview. Vercel Deployment Protection may require visitors to sign in on protected deployments.

### Security and limitations

This is a **casual, unauthenticated leaderboard**, not a cheat-proof competition. The API validates nicknames and score bounds, ignores duplicate round IDs, and keeps database credentials server-side. It does **not** verify that a real 60-second round was played; an attacker can forge scores or generate new round IDs. Nicknames are unmoderated, and the endpoint has no application-level rate limiter.

Before widely publicizing it, configure rate limiting for `/api/scores` in Vercel Firewall (according to your plan's availability), monitor usage, and moderate unwanted rows through Supabase. For competitive play, add server-issued rounds and server-verified answers, plus bot protection/authentication. Do not rely on an in-memory rate limiter in a serverless function.

## Tests

From this game folder:

```sh
npm test
```

Or from the repository root:

```sh
npm --prefix games/quantum-arithmetic test
```

Tests use Node's built-in test runner and mocked Supabase responses, so they require no credentials. They do not connect to a live database or deploy to Vercel.
