// Only explicit saves enter localStorage. Drafts/results stay in this browser tab.
export const HISTORY_KEY = 'path2placement.history.v2';
export const MAX_RECORDS = 200;
export const CATEGORY_NAMES = ['Academic preparation', 'Programming & DSA', 'Projects & experience', 'Aptitude & communication', 'Interview & resume'];
export function isRecord(record) {
  return !!record && typeof record.id === 'string' && /^[a-zA-Z0-9-]{10,80}$/.test(record.id)
    && typeof record.created_at === 'string' && Number.isFinite(Date.parse(record.created_at))
    && !!record.inputs && typeof record.inputs === 'object' && !Array.isArray(record.inputs)
    && Number.isFinite(record.score) && record.score >= 0 && record.score <= 100
    && typeof record.band === 'string' && !!record.categories
    && CATEGORY_NAMES.every(c => Number.isFinite(record.categories[c]) && record.categories[c] >= 0 && record.categories[c] <= 100)
    && Array.isArray(record.missing_optional) && typeof record.scoring_version === 'string'
    && Array.isArray(record.recommendations) && Array.isArray(record.plan);
}
export function readHistory(storage = localStorage) {
  const raw = storage.getItem(HISTORY_KEY);
  if (!raw) return [];
  const records = JSON.parse(raw);
  if (!Array.isArray(records) || records.length > MAX_RECORDS || !records.every(isRecord)) throw new Error('Saved history could not be read. Export a backup if available, or clear the damaged browser history in Privacy & data.');
  return records.sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));
}
export function saveAssessment(record, storage = localStorage) {
  if (!isRecord(record)) throw new Error('This assessment is incomplete. Please calculate it again before saving.');
  const records = readHistory(storage);
  if (records.some(r => r.id === record.id)) return records;
  if (records.length >= MAX_RECORDS) throw new Error('This browser has 200 saved assessments. Export a backup and clear history before saving more.');
  records.push(record);
  storage.setItem(HISTORY_KEY, JSON.stringify(records));
  return records;
}
export function clearHistory(storage = localStorage) { storage.removeItem(HISTORY_KEY); }
export function csvCell(value) {
  let text = value == null ? '' : String(value);
  if (/^[=+@\-\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}
export function historyCsv(records) {
  const fields = [...new Set(records.flatMap(r => Object.keys(r.inputs)))];
  const headers = ['assessment_id','timestamp_utc','readiness_score','band','scoring_version', ...CATEGORY_NAMES, ...fields];
  return [headers, ...records.map(r => [r.id,r.created_at,r.score,r.band,r.scoring_version, ...CATEGORY_NAMES.map(c => r.categories[c]), ...fields.map(f => r.inputs[f])])].map(row => row.map(csvCell).join(',')).join('\r\n');
}
export function parseBackup(text) {
  if (text.length > 2_000_000) throw new Error('Use a backup file smaller than 2 MB.');
  let data;
  try { data = JSON.parse(text); } catch { throw new Error('This is not a valid JSON backup. Choose a Path2Placement backup file.'); }
  if (data.version !== 2 || !Array.isArray(data.assessments) || !data.assessments.length || data.assessments.length > MAX_RECORDS || !data.assessments.every(isRecord)) throw new Error('This backup has an unsupported or incomplete assessment format.');
  if (new Set(data.assessments.map(r => r.id)).size !== data.assessments.length) throw new Error('This backup contains duplicate assessment IDs.');
  return data.assessments;
}
