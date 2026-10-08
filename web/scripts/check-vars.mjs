// Comprueba que business.json está completo antes de publicar (npm run release).
import { readFileSync } from 'node:fs';

const biz = JSON.parse(readFileSync(new URL('../src/data/business.json', import.meta.url), 'utf-8'));
const REQUIRED = [
  'marca', 'dominio', 'telefono', 'whatsapp', 'email', 'calle', 'cp', 'localidad', 'provincia', 'lat', 'lng',
  'abre', 'cierra', 'form_endpoint', 'titular_legal', 'nif', 'domicilio_legal', 'empresa_ejecutora',
];
const missing = REQUIRED.filter((key) => String(biz[key] ?? '').trim() === '');
if (missing.length) {
  console.error(`✗ Faltan datos del negocio en src/data/business.json: ${missing.join(', ')}`);
  process.exit(1);
}
console.log('✓ Datos del negocio completos');
