import type { APIRoute } from 'astro';
import data from '../data/pages.json';
import { siteUrl } from '../lib/site';

const PRIORITY: Record<string, string> = {
  home: '1.0', pillar: '0.8', 'service-area': '0.7', hub: '0.7', presupuesto: '0.5', proyectos: '0.5',
  'sobre-nosotros': '0.3',
};

export const GET: APIRoute = () => {
  const base = siteUrl() || 'https://{{dominio}}';
  const urls = data.pages
    .filter((p: any) => !p.noindex)
    .map((p: any) => `<url><loc>${base}${p.route}</loc><lastmod>${data.generado}</lastmod><priority>${PRIORITY[p.type] ?? '0.5'}</priority></url>`)
    .join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
