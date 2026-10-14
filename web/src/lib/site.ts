import { existsSync } from 'node:fs';
import { join } from 'node:path';
import business from '../data/business.json';
import data from '../data/pages.json';
import areas from '../data/areas-served.json';

// pages.json lo genera scripts/landing_generator.py; business.json lo rellena el usuario.
export const pages: any[] = data.pages;
export const biz: Record<string, any> = business;
export const coverage: string[] = areas.cobertura;

export const REQUIRED = [
  'marca', 'dominio', 'telefono', 'whatsapp', 'email', 'calle', 'cp', 'localidad', 'provincia', 'lat', 'lng',
  'abre', 'cierra', 'form_endpoint', 'titular_legal', 'nif', 'domicilio_legal', 'empresa_ejecutora',
];
const filled = (key: string) => String(biz[key] ?? '').trim() !== '';
export const pending = REQUIRED.filter((key) => !filled(key));
/** Solo se indexa con "indexable": true en business.json y todos los datos rellenos. */
export const indexable = biz.indexable === true && pending.length === 0;

const TOKEN = /\{\{(\w+)\}\}/g;

/** Sustituye {{variable}} por su valor en business.json; si está vacío, deja la variable visible. */
export function fill(text = ''): string {
  return text.replace(TOKEN, (token, key) => (filled(key) ? String(biz[key]) : token));
}

export function fillDeep<T>(value: T): T {
  if (typeof value === 'string') return fill(value) as T;
  if (Array.isArray(value)) return value.map(fillDeep) as T;
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, fillDeep(v)])) as T;
  }
  return value;
}

/** JSON-LD sin propiedades cuyo dato sigue pendiente ({{variable}} vacía): Google no debe ver texto de plantilla. */
export function pruneTokens(value: any): any {
  if (Array.isArray(value)) return value.map(pruneTokens).filter((v) => v !== undefined);
  if (value && typeof value === 'object') {
    const out = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, pruneTokens(v)])
      .filter(([, v]) => v !== undefined && !(Array.isArray(v) && v.length === 0)));
    return Object.keys(out).length ? out : undefined;
  }
  return typeof value === 'string' && /\{\{\w+\}\}/.test(value) ? undefined : value;
}

/** true si el archivo existe en public/ (fotos que aún no se han subido se muestran como hueco en desarrollo). */
export const hasPublicFile = (src: string) => existsSync(join(process.cwd(), 'public', src));

/** Versión móvil (…-800.webp) de una imagen grande, si se ha generado. */
export function mobileVariant(src: string): string | undefined {
  const variant = src.replace(/\.webp$/, '-800.webp');
  return variant !== src && hasPublicFile(variant) ? variant : undefined;
}

/** Enlace al formulario con el servicio y la zona ya elegidos. */
export function quoteHref(servicio?: string, zona?: string): string {
  const params = new URLSearchParams();
  if (servicio) params.set('servicio', servicio);
  if (zona) params.set('zona', zona);
  return '/presupuesto/' + (params.size ? `?${params}` : '');
}

export const pageByRoute = (route: string) => pages.find((p) => p.route === route);
export const services = pages.filter((p) => p.type === 'pillar');
export const hubs = pages.filter((p) => p.type === 'hub');

export function siteUrl(): string {
  const dominio = String(biz.dominio || '').replace(/^https?:\/\//, '').replace(/\/$/, '');
  return dominio ? `https://${dominio}` : '';
}

export const phoneLabel = () => biz.telefono_visible || biz.telefono || '{{telefono}}';
export const telHref = () => (filled('telefono') ? `tel:${String(biz.telefono).replace(/\s+/g, '')}` : '/presupuesto/');
/** WhatsApp con mensaje que identifica la marca (y el servicio si se conoce) para saber de dónde llega el contacto. */
export function waHref(servicio?: string): string {
  if (!filled('whatsapp')) return '/presupuesto/';
  const name = servicio ? pages.find((p) => p.type === 'pillar' && p.params.servicio === servicio)?.h1 : '';
  const text = `Hola, os escribo desde la web de ${biz.marca || 'la carpintería'}. Quiero pedir presupuesto` +
    (name ? ` para ${name.charAt(0).toLowerCase()}${name.slice(1)}.` : '.');
  return `https://wa.me/${String(biz.whatsapp).replace(/\D/g, '')}?text=${encodeURIComponent(text)}`;
}

/** URL del mapa de la ficha de Google: acepta la URL de inserción o el <iframe> completo copiado de Google Maps. */
export function mapsEmbedSrc(): string {
  const raw = String(biz.maps_embed_url || '').trim();
  const src = raw.match(/src="([^"]+)"/)?.[1] ?? raw;
  if (/^https:\/\/(www\.)?google\.[a-z.]+\/maps\/embed/.test(src)) return src.replace(/&amp;/g, '&');
  // Sin ficha todavía: mapa de Google a partir de la dirección (no necesita clave de API).
  const address = ['calle', 'cp', 'localidad'].map((k) => String(biz[k] ?? '').trim());
  if (address.every(Boolean)) {
    const query = encodeURIComponent(`${address[0]}, ${address[1]} ${address[2]}, España`);
    return `https://maps.google.com/maps?q=${query}&z=17&hl=es&output=embed`;
  }
  return '';
}

export const slugify = (text: string) =>
  text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
