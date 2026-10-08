import type { APIRoute } from 'astro';
import { indexable, siteUrl } from '../lib/site';

// Rastreo bloqueado hasta "indexable": true en business.json (y sin datos pendientes).
export const GET: APIRoute = () => {
  const rules = indexable ? 'Allow: /' : 'Disallow: /';
  const sitemap = indexable ? `\nSitemap: ${siteUrl()}/sitemap.xml\n` : '';
  return new Response(`User-agent: *\n${rules}\n${sitemap}`, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
