import { showDemoPaused, showRateLimitCTA } from './cta.js';

// The Cloud Run API (VITE_API_BASE, set on Vercel at build time).
const API = ((import.meta.env.VITE_API_BASE || 'http://localhost:8000') + '').replace(/\/+$/, '');

export class LimitError extends Error {}

async function request(path, options) {
  const r = await fetch(API + path, options);
  const data = await r.json().catch(() => ({}));
  // AI Lodge limit: 429 = this visitor reached the demo's limit (CTA), 503 = the demo is paused. No substitute run.
  if (r.status === 429) {
    showRateLimitCTA(data.detail?.queries_used ?? 'a few');
    throw new LimitError("You've reached this demo's limit for live attacks.");
  }
  if (r.status === 503) {
    showDemoPaused(data.detail?.message);
    throw new LimitError('The demo is paused right now.');
  }
  if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.');
  return data;
}

export const getOverview = () => request('/api/overview');
export const getHealth = () => request('/api/health');
export const runAttack = (body) =>
  request('/api/attack', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
