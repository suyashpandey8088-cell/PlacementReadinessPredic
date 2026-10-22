export const MIN_PASSWORD = 8;
export const MAX_PASSWORD = 128;

export function normalizeEmail(value) {
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
}

export function validateEmail(value) {
  const email = normalizeEmail(value);
  return email.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

export function passwordProblem(value) {
  if (typeof value !== 'string' || !value.trim()) return 'Enter a password.';
  if (value.length < MIN_PASSWORD) return `Use at least ${MIN_PASSWORD} characters.`;
  if (value.length > MAX_PASSWORD) return `Use a password shorter than ${MAX_PASSWORD + 1} characters.`;
  return '';
}

export function accountInitial(email) {
  return (typeof email === 'string' ? email.trim().charAt(0) : '')?.toUpperCase() || '?';
}

export function safeNextPath(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return '/progress';
  try {
    const base = 'https://path2placement.invalid';
    const target = new URL(value, base);
    if (target.origin !== base) return '/progress';
    if (target.pathname === '/login') return '/progress';
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return '/progress';
  }
}

export function shortEmail(email, max = 30) {
  const value = typeof email === 'string' ? email : '';
  return value.length > max ? `${value.slice(0, Math.max(1, max - 1))}…` : value;
}
