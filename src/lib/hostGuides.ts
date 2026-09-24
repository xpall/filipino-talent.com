// Maps a submitted DNS target to the "connect your subdomain" guide section.
// Frontend-only: this drives deep links, not validation. The validation list is
// `targets.ts` (kept in sync with the backend's allowed-targets.json).

export interface HostConnect {
  suffix: string;
  label: string;
  anchor: string;
}

export const HOST_CONNECT: HostConnect[] = [
  { suffix: 'github.io', label: 'GitHub Pages', anchor: 'github-pages' },
  { suffix: 'pages.dev', label: 'Cloudflare Pages', anchor: 'cloudflare-pages' },
  { suffix: 'vercel.app', label: 'Vercel', anchor: 'vercel' },
  { suffix: 'netlify.app', label: 'Netlify', anchor: 'netlify' },
];

export const CONNECT_GUIDE_PATH = '/guide/connect';

export function connectGuideForTarget(target: string): HostConnect | undefined {
  const value = String(target ?? '')
    .trim()
    .toLowerCase()
    .replace(/\.$/, '');
  return HOST_CONNECT.find((host) => value === host.suffix || value.endsWith(`.${host.suffix}`));
}
