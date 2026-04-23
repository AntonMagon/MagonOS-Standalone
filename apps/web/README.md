# MagonOS Web UI

Canonical public/product shell for the standalone platform.

This directory is the active frontend-of-record.
The old copy in `/Users/anton/Desktop/MagonOS/MagonOS/apps/web` is legacy donor code only.

## Run
```bash
cd /Users/anton/Desktop/MagonOS-Standalone
./scripts/run_foundation_unified.sh --fresh
```

Primary local URL: `http://127.0.0.1:3000`

The canonical local runtime now starts the production web bundle by default.
Use `MAGON_WEB_RUNTIME=dev` only for explicit frontend debugging.

Direct standalone-only frontend development still works:

```bash
cd /Users/anton/Desktop/MagonOS-Standalone/apps/web
npm install
MAGON_WEB_DIST_DIR=.next-dev npm run dev
```

When running the frontend by itself, point it at the standalone backend with:

```bash
MAGON_API_BASE_URL=http://127.0.0.1:8091 MAGON_WEB_DIST_DIR=.next-dev npm run dev
```

## Verify
```bash
cd /Users/anton/Desktop/MagonOS-Standalone/apps/web
npm run lint
npm run build
npm run typecheck
```

Important:
- `npm run typecheck` already runs `next typegen` first, so it no longer depends on a prior `next build` or `next dev`
- keep `MAGON_WEB_DIST_DIR=.next-dev` for dev mode if you want to avoid collisions with a separate `next build`
- RU: Автоматизации и обычный локальный runtime должны идти через foundation launcher, а не через legacy compatibility wrappers.

## Design system
- Core primitives live in `components/ui/`
- Public exports live in `design-system/index.ts`
- Tokens live in `design-system/tokens.ts`
- Theme variables live in `app/globals.css`
- `components.json` keeps the project compatible with `shadcn` registries and MagicUI additions

## Localization
- Default locale config: `i18n/config.ts`
- Request config for `next-intl`: `i18n/request.ts`
- Russian messages: `messages/ru.json`

### Add new strings
1. Add a new key to `messages/ru.json`
2. Read the string via `useTranslations()` in client components or `getTranslations()` in server components
3. Do not hardcode user-facing text in JSX, including `aria-label`, button text, empty states, and helper text

### Add a future language
1. Create `messages/<locale>.json`
2. Add the locale to `i18n/config.ts`
3. Keep the same key structure across all locale files
4. Do not rename keys casually; treat them as API contracts for the UI

### Translation style
- Use short operational language
- Prefer product terms that match the actual workflow
- Keep labels compact and helper text explicit
- Avoid decorative or ambiguous wording

## Library choice
- `shadcn` + Radix primitives: system base
- `@magicuidesign/cli`: registry tooling for optional hero/effects components
- `lightswind`: evaluated but not adopted as a runtime dependency because its published npm artifact is currently not reliable enough for the core system
