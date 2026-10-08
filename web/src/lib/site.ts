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

export const pageByRoute = (route: string) => pages.find((p) => p.route === route);
export const services = pages.filter((p) => p.type === 'pillar');
export const hubs = pages.filter((p) => p.type === 'hub');

export function siteUrl(): string {
  const dominio = String(biz.dominio || '').replace(/^https?:\/\//, '').replace(/\/$/, '');
  return dominio ? `https://${dominio}` : '';
}

export const phoneLabel = () => biz.telefono_visible || biz.telefono || '{{telefono}}';
export const telHref = () => (filled('telefono') ? `tel:${String(biz.telefono).replace(/\s+/g, '')}` : '/presupuesto/');
export const waHref = (text = 'Hola, quiero pedir presupuesto') =>
  filled('whatsapp') ? `https://wa.me/${String(biz.whatsapp).replace(/\D/g, '')}?text=${encodeURIComponent(text)}` : '/presupuesto/';

export const slugify = (text: string) =>
  text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
