import type { APIRoute } from 'astro';
import { pending, siteUrl } from '../lib/site';

// Con datos del negocio pendientes se bloquea el rastreo: así no se indexa una web con {{variables}}.
export const GET: APIRoute = () => {
  const rules = pending.length ? 'Disallow: /' : 'Allow: /';
  const body = `User-agent: *\n${rules}\n\nSitemap: ${siteUrl() || 'https://{{dominio}}'}/sitemap.xml\n`;
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
