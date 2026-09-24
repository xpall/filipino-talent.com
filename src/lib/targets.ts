// Keep in sync with filipino-talent-backend/config/allowed-targets.json.
// The backend remains the source of truth; this list is only used to warn
// users about an unsupported CNAME target before they submit.
export const ALLOWED_CNAME_SUFFIXES = [
  'github.io',
  'pages.dev',
  'netlify.app',
  'vercel.app',
  'web.app',
  'firebaseapp.com',
  'glitch.me',
  'onrender.com',
  'fly.dev',
  'railway.app',
  'up.railway.app',
  'surge.sh',
  'carrd.co',
  'framer.app',
  'framer.website',
  'readthedocs.io',
  'gitlab.io',
  'hashnode.dev',
  'duckdns.org',
  'azurewebsites.net',
  'ondigitalocean.app',
];

export function hostnameFromUrl(value: string): string {
  try {
    const url = new URL(value.trim());
    return url.hostname.toLowerCase().replace(/\.$/, '');
  } catch {
    return '';
  }
}

export function isAllowedCnameTarget(host: string): boolean {
  const value = host.trim().toLowerCase().replace(/\.$/, '');
  if (!value) return false;
  return ALLOWED_CNAME_SUFFIXES.some((suffix) => value === suffix || value.endsWith(`.${suffix}`));
}
