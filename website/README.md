# TrustLens SG — public website

Marketing and explainer site for TrustLens SG: the problem, the rationale, the
features, the roadmap, and a call to action that opens the Telegram bot.

Built with **Vite + React + TypeScript**, **Tailwind CSS**, **shadcn/ui**
components and **lucide-react** icons. No emoji are used anywhere in the UI.

## Run it

```bash
npm install
npm run dev
```

Then open the URL Vite prints (http://localhost:5173 by default).

Other scripts:

- `npm run build` — typecheck, then produce a production build in `dist/`
- `npm run preview` — serve the production build locally
- `npm run typecheck` — TypeScript only

## Where to change things

| What | File |
|------|------|
| Telegram bot handle and link | `src/lib/utils.ts` (`TELEGRAM_BOT_HANDLE`, `TELEGRAM_BOT_URL`) |
| Section order on the page | `src/App.tsx` |
| Header navigation and advisory bar | `src/components/site-header.tsx` |
| Footer links and research references | `src/components/site-footer.tsx` |
| Hero copy and the example verdict card | `src/components/sections/hero.tsx` |
| The five gaps and the statistics strip | `src/components/sections/problem.tsx` |
| Design principles and user personas | `src/components/sections/rationale.tsx` |
| Four steps and the verdict legend | `src/components/sections/how-it-works.tsx` |
| Feature list and their status badges | `src/components/sections/features.tsx` |
| Outcomes and the KPI table | `src/components/sections/impact.tsx` |
| Roadmap phases and scalability | `src/components/sections/roadmap.tsx` |
| Data handling commitments | `src/components/sections/governance.tsx` |
| Frequently asked questions | `src/components/sections/faq.tsx` |
| Closing call to action | `src/components/sections/cta-band.tsx` |

Each section keeps its copy in a plain array at the top of the file, so editing
text never means touching layout code.

## Design decisions

The site is aimed at adults aged 40 to 65, so it is deliberately plain:

- White background, one navy accent, thin grey rules. No gradients or imagery
  that could read as advertising.
- Body text is 17px on small screens and 18px from the medium breakpoint up,
  with a 1.65 line height.
- Every section is a labelled landmark with a real `h2`, and the page opens with
  a skip link.
- Feature and roadmap items carry an honest status badge: *Available now*,
  *In development*, or *Planned*. Nothing unbuilt is described as working.
- An advisory bar at the top states that this is an independent student project
  and not a government service, so the official-looking styling cannot be
  mistaken for an official-agency claim.

## Adding more shadcn/ui components

`components.json` is configured, so the CLI works as normal:

```bash
npx shadcn@latest add dialog
```

Components land in `src/components/ui/`.
