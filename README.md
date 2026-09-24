# filipino-talent.com (web)

Astro site for **filipino-talent.com**: landing page, beginner guide, submit
form, and the public subdomain directory. Deployed to Cloudflare Pages.

The backend (registry, DNS automation, API Worker) lives in the
`filipino-talent-backend` repository.

## Stack

- [Astro](https://astro.build) (static output) with MDX
- Plain CSS, no UI framework
- Talks to the API Worker at `PUBLIC_API_BASE`

## Local development

```bash
npm install
cp .env.example .env    # optional; defaults to https://api.filipino-talent.com
npm run dev             # http://localhost:4321
```

For local work against a local Worker, set `PUBLIC_API_BASE=http://localhost:8787`
in `.env`.

## Build

```bash
npm run build           # outputs to dist/
npm run preview
```

## Deploy (Cloudflare Pages)

1. Create a Pages project connected to this repository.
2. Build command: `npm run build`
3. Build output directory: `dist`
4. Environment variable: `PUBLIC_API_BASE=https://api.filipino-talent.com`
5. Add the custom domains `filipino-talent.com` and `www.filipino-talent.com`,
   and set up a redirect from `www` to the apex.

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Landing page |
| `/guide` | Step-by-step tutorial and host chooser |
| `/guide/connect` | Final step: connect the subdomain at GitHub Pages, Cloudflare Pages, Vercel, or Netlify |
| `/guide/*` | Per-host guides (GitHub Pages, Cloudflare Pages, Netlify, Vercel, Canva, troubleshooting) |
| `/submit` | Request form |
| `/directory` | Public list of claimed subdomains |
| `/terms` | Terms of Use |

## Environment variables

| Name | Description |
| --- | --- |
| `PUBLIC_API_BASE` | Base URL of the backend Worker (no trailing slash) |
