# SIGQuantum games

A collection of quantum games. Each game lives in its own self-contained folder and can be deployed independently.

## Games

| Game | Folder | Description |
| --- | --- | --- |
| Quantum arithmetic | [`games/quantum-arithmetic`](games/quantum-arithmetic) | A minimal, 60-second quantum-gate quiz with a Supabase leaderboard. |

```text
games/
  quantum-arithmetic/
    index.html
    game.js
    leaderboard.js
    style.css
    api/
    supabase/
    tests/
    package.json
    .env.example
    README.md
```

Add future games under `games/<game-name>/`, keeping their assets, APIs, dependencies, tests, and setup instructions inside that folder. No shared build system or workspace setup is required.

## Host each game separately on Vercel

Create **one Vercel project per game**, all connected to this same GitHub repository. You do not need separate repositories or branches.

1. In Vercel, choose **Add New → Project** and import this repository.
2. Give the project a game-specific name, such as `sigquantum-arithmetic`.
3. Set **Root Directory** to `games/quantum-arithmetic`.
4. For this vanilla game, choose **Framework Preset: Other**, leave **Build Command** empty, and set **Output Directory** to `.`. Paths are relative to the selected Root Directory. Use Node.js 22.x.
5. Add the environment variables described in the [game's setup guide](games/quantum-arithmetic/README.md), then deploy.
6. For the next game, import the **same repository again** as a new Vercel project, choosing that game's folder and its own build settings.

Each Vercel project has its own:

- Public `*.vercel.app` URL, with optional custom domains/subdomains.
- Environment variables and deployment history.
- Static assets and API routes. `/api/scores` on the arithmetic domain belongs only to arithmetic.

For example (illustrative URLs):

| Vercel project | Root Directory | URL |
| --- | --- | --- |
| `sigquantum-arithmetic` | `games/quantum-arithmetic` | `sigquantum-arithmetic.vercel.app` |
| A future game | `games/<game-name>` | `<game-name>.vercel.app` |

Git pushes can trigger deployments for multiple connected projects; a separate project does not automatically mean only changes in that game's folder trigger a deployment. Vercel offers ignored-build settings, and automatic unaffected-project skipping for eligible workspace-based monorepos. This repository intentionally keeps the simpler independent-folder layout.

### If arithmetic is already deployed

Update the **existing project's Settings → Build and Deployment → Root Directory** to `games/quantum-arithmetic`, keep Output Directory as `.`, and redeploy the commit containing this move. This keeps its existing URL, domains, and environment variables. No Supabase migration or new table is needed just because files moved.

### Supabase for multiple games

The arithmetic project needs `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in its Vercel environment. Variables are not automatically shared with other Vercel projects.

You can use a separate Supabase project per game for isolation, or share one Supabase project using distinct tables per game. Its secret key has broad database access, so separate tables alone are not a security boundary. The arithmetic game's table is `quantum_scores`.

## Develop and test

Open `games/quantum-arithmetic/index.html` to play without the shared leaderboard.

From the repository root, run its tests:

```sh
npm --prefix games/quantum-arithmetic test
```

For local API development, run `npx vercel link` from the repository root and select the appropriate Vercel project, then run `npx vercel dev`. See the [game README](games/quantum-arithmetic/README.md) for environment setup. To work on a different game's project, link again and select that project.
