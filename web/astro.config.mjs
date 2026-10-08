import { readFileSync } from 'node:fs';
import { defineConfig } from 'astro/config';

const business = JSON.parse(readFileSync(new URL('./src/data/business.json', import.meta.url), 'utf-8'));
const dominio = String(business.dominio || '').replace(/^https?:\/\//, '').replace(/\/$/, '');

export default defineConfig({
  site: dominio ? `https://${dominio}` : undefined,
  trailingSlash: 'always',
  build: { format: 'directory' },
  compressHTML: true,
});
