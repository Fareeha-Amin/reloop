# frontend/

The ReLoop web app: React 19, Vite, Tailwind 4, React Router, TanStack Query, Leaflet.
Setup, commands and limitations are in the [root README](../README.md); decisions are
in [CLAUDE.md](../CLAUDE.md).

```
npm install
npm run dev        # http://localhost:5173; start the backend (uvicorn, port 8000) first
npm test
```

Rules this code follows:

- **The API decides; the UI renders.** Buttons come from `allowed_actions`. API
  vocabulary values appear only in `src/vocab/` (`tests/no-literals.test.ts`).
- **Strings** live in `src/i18n/en.json` and are read with `t()` (`tests/locale.test.ts`).
- **Styling** comes from tokens in `src/styles/theme.css`, used by `src/ui/`. Pages
  compose `src/ui/` and `src/components/`. Each colour token is a light/dark pair
  (`light-dark()`); `src/ui/theme.ts` sets `data-theme` on `<html>` from the header
  toggle or, by default, the system setting.
- **The admin donation record is never polled.** Each load is recorded as an address
  access (`useAdminDonation` in `src/app/queries.ts`).
- **API types** are generated (`npm run gen:api`) from `src/api/openapi.json`, which the
  backend writes (`python -m app.cli export-openapi`). Never edit `src/api/schema.ts`.
