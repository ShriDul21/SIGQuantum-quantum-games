# SIGQuantum games

A collection of quantum games. Each game lives in its own self-contained folder and can be deployed independently.

## Games

| Game | Folder | Description |
| --- | --- | --- |
| Quantum arithmetic | [`games/quantum-arithmetic`](games/quantum-arithmetic) | A minimal, 60-second quantum-gate quiz with a Supabase leaderboard. |
| Quantum Poker | [`games/quantum-poker`](games/quantum-poker) | A local Python/Tkinter quantum poker game with Qiskit. |

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
    vercel.json
  quantum-poker/
    Python/
    tests/
    gui.py
    requirements-gui.txt
    README.md
```

Add future games under `games/<game-name>/`, keeping their assets, APIs, dependencies, tests, and setup instructions inside that folder. No shared build system or workspace setup is required.

## Host each game separately on Vercel

Create **one Vercel project per game**, all connected to this same GitHub repository. You do not need separate repositories or branches.

1. In Vercel, choose **Add New → Project** and import this repository.
2. Give the project a game-specific name, such as `sigquantum-arithmetic`.
3. Set **Root Directory** to `games/quantum-arithmetic` and **Production Branch** to `main`.
4. For this vanilla game, choose **Framework Preset: Other**, leave **Build Command** empty, and set **Output Directory** to `.`. The game's `vercel.json` also records these build settings. Paths are relative to the selected Root Directory. Use Node.js 22.x.
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

### Troubleshooting arithmetic 404s

- Check the deployment's source branch and commit. Use **`main`**, not `master`; `master` contains the original standalone Python poker game, not the arithmetic website.
- Set the Vercel project's **Root Directory** to exactly `games/quantum-arithmetic`. The repository root has no `index.html`.
- **Output Directory** is `.` relative to that root, **not** `games/quantum-arithmetic`, `public`, or `dist`. There is no build step generating a `dist` folder.
- Deploy the latest commit after changing settings. Redeploying an older commit does not pick up newer files. Open the new deployment's own URL to rule out an outdated custom-domain target.
- Visit `/` on the arithmetic deployment, not `/games/quantum-arithmetic/`. Its API is `/api/scores`; missing Supabase variables return a JSON 503, not a missing-page 404.

### Quantum Poker is a desktop game

The former `master` branch's history is merged into `main`, with its files under `games/quantum-poker/`. It requires Python, Tkinter, and a graphical desktop; it cannot run as a Vercel website without a separate web port. Run it locally from its own folder:

```sh
cd games/quantum-poker
python3 -m pip install -r requirements-gui.txt
python3 gui.py
```

See the [Poker README](games/quantum-poker/README.md) for rules, tests, and original project documentation. Its original license is preserved in that folder.

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
