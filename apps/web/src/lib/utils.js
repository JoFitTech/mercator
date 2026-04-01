import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const ALLOWED_EXCHANGES = new Set(['NYSE', 'NASDAQ', 'XETRA', 'EURONEXT', 'LSE', 'TSX', 'SIX']);
const EXCHANGE_ALIASES = { XETR: 'XETRA', XETRA: 'XETRA', NASDAQGS: 'NASDAQ', NASDAQGM: 'NASDAQ', NYSEARCA: 'NYSE', ENX: 'EURONEXT' };
const VALID_GATE_STATUS = new Set(['PASS', 'FAIL', 'OFFEN']);

const asText = (v) => (v === null || v === undefined ? '' : String(v).trim());
const asNum = (v) => {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
const asBool = (v) => {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'number') return v !== 0;
  if (typeof v === 'string') {
    const t = v.trim().toLowerCase();
    if (['true', 'ja', 'yes', '1'].includes(t)) return true;
    if (['false', 'nein', 'no', '0'].includes(t)) return false;
  }
  return null;
};

export function normalizeIdentifierInput({ isin, wkn, ticker }) {
  const normalized = { isin: asText(isin).toUpperCase(), wkn: asText(wkn).toUpperCase(), ticker: asText(ticker).toUpperCase() };
  const lookup = normalized.isin || normalized.wkn || normalized.ticker;
  const lookupType = normalized.isin ? 'isin' : normalized.wkn ? 'wkn' : normalized.ticker ? 'ticker' : '';
  return { ...normalized, lookup, lookupType };
}

export function normalizeBaseData(raw = {}) {
  const exchangeRaw = asText(raw.exchange).toUpperCase();
  return {
    ticker: asText(raw.ticker || raw.symbol).toUpperCase(),
    companyName: asText(raw.companyName || raw.name),
    assetType: asText(raw.assetType || raw.type),
    isin: asText(raw.isin).toUpperCase(),
    wkn: asText(raw.wkn).toUpperCase(),
    exchange: EXCHANGE_ALIASES[exchangeRaw] || exchangeRaw,
    country: asText(raw.country),
    region: asText(raw.region),
    sector: asText(raw.sector),
    currency: asText(raw.currency || raw.ccy).toUpperCase(),
    price: asNum(raw.price),
    marketCap: asNum(raw.marketCap),
    avgDollarVolume: asNum(raw.avgDollarVolume),
    spreadPct: asNum(raw.spreadPct),
    earningsDate: asText(raw.earningsDate),
    daysToEarnings: asNum(raw.daysToEarnings),
    ttmFcf: asNum(raw.ttmFcf),
    netCashFlag: asBool(raw.netCashFlag),
    runwayMonths: asNum(raw.runwayMonths),
    revenueCagr3y: asNum(raw.revenueCagr3y),
    marginTrend: asText(raw.marginTrend).toLowerCase(),
    dilutionTrend: asText(raw.dilutionTrend).toLowerCase(),
    volatilityBucket: asText(raw.volatilityBucket).toLowerCase(),
    terPct: asNum(raw.terPct),
    domicile: asText(raw.domicile),
    replicationMethod: asText(raw.replicationMethod),
    trackingDifferencePct: asNum(raw.trackingDifferencePct)
  };
}

export function deriveAutoGates(data) {
  const gates = {};
  const mcap = data.marketCap;
  const vol = data.avgDollarVolume;
  const spread = data.spreadPct;
  const dte = data.daysToEarnings;
  const exchangeKnown = Boolean(data.exchange);
  const exchangeAllowed = exchangeKnown ? ALLOWED_EXCHANGES.has(data.exchange) : null;

  let hardViolations = 0;
  if (mcap !== null && mcap < 1e9) hardViolations += 1;
  if (vol !== null && vol < 1e7) hardViolations += 1;
  if (spread !== null && spread > 0.3) hardViolations += 1;

  if ((exchangeKnown && exchangeAllowed === false) || hardViolations >= 2) gates.gateUniverseLiquidity = 'FAIL';
  else if (exchangeAllowed && mcap >= 1e9 && vol >= 1e7 && spread <= 0.3) gates.gateUniverseLiquidity = 'PASS';
  else gates.gateUniverseLiquidity = 'OFFEN';

  if (data.netCashFlag === true || (data.ttmFcf !== null && data.ttmFcf > 0) || (data.runwayMonths !== null && data.runwayMonths >= 18)) gates.gateRunway = 'PASS';
  else gates.gateRunway = 'OFFEN';

  gates.gateEdgeProof = 'OFFEN';

  if (data.revenueCagr3y !== null && data.marginTrend && data.revenueCagr3y >= 10 && ['stabil', 'verbessernd'].includes(data.marginTrend)) gates.gateGrowthConvexity = 'PASS';
  else if (data.revenueCagr3y !== null && data.marginTrend === 'verschlechternd' && data.revenueCagr3y < 5) gates.gateGrowthConvexity = 'FAIL';
  else gates.gateGrowthConvexity = 'OFFEN';

  gates.gateGovernance = 'OFFEN';

  if ((dte !== null && dte < 7) || (vol !== null && vol < 1e7) || (spread !== null && spread > 0.3)) gates.gateTradingFeasibility = 'FAIL';
  else if (vol !== null && spread !== null && vol >= 1e7 && spread <= 0.3 && (dte === null || dte >= 7)) gates.gateTradingFeasibility = 'PASS';
  else gates.gateTradingFeasibility = 'OFFEN';

  return gates;
}

export function deriveAutoScores(data) {
  const scores = { scoreEdgeStrength: 0, scoreQuality: 0, scoreGrowthLeverage: 0, scoreSatelliteFit: 0 };
  if (data.ttmFcf !== null && data.ttmFcf > 0) scores.scoreQuality += 10;
  if (data.netCashFlag === true) scores.scoreQuality += 10;
  if (data.dilutionTrend === 'niedrig') scores.scoreQuality += 5;
  else if (data.dilutionTrend === 'stabil') scores.scoreQuality += 3;
  scores.scoreQuality = Math.min(scores.scoreQuality, 25);

  if (data.revenueCagr3y !== null) {
    if (data.revenueCagr3y >= 20) scores.scoreGrowthLeverage += 15;
    else if (data.revenueCagr3y >= 10) scores.scoreGrowthLeverage += 10;
    else if (data.revenueCagr3y >= 5) scores.scoreGrowthLeverage += 5;
  }
  if (data.marginTrend === 'verbessernd') scores.scoreGrowthLeverage += 10;
  else if (data.marginTrend === 'stabil') scores.scoreGrowthLeverage += 6;
  scores.scoreGrowthLeverage = Math.min(scores.scoreGrowthLeverage, 25);

  if (data.avgDollarVolume !== null) {
    if (data.avgDollarVolume >= 5e7) scores.scoreSatelliteFit += 8;
    else if (data.avgDollarVolume >= 1e7) scores.scoreSatelliteFit += 5;
  }
  if (data.spreadPct !== null) {
    if (data.spreadPct <= 0.1) scores.scoreSatelliteFit += 6;
    else if (data.spreadPct <= 0.3) scores.scoreSatelliteFit += 3;
  }
  if (['niedrig', 'low'].includes(data.volatilityBucket)) scores.scoreSatelliteFit += 6;
  else if (['mittel', 'medium'].includes(data.volatilityBucket)) scores.scoreSatelliteFit += 4;
  else if (data.volatilityBucket) scores.scoreSatelliteFit += 2;
  if (data.daysToEarnings !== null && data.daysToEarnings < 7) scores.scoreSatelliteFit = Math.max(0, scores.scoreSatelliteFit - 2);
  scores.scoreSatelliteFit = Math.min(scores.scoreSatelliteFit, 20);

  return scores;
}

export function buildAutoDataNote({ normalizedData, gates, scores }) {
  const present = Object.entries(normalizedData).filter(([, v]) => v !== '' && v !== null).map(([k]) => k);
  const openGates = Object.entries(gates).filter(([, v]) => v === 'OFFEN').map(([k]) => k);
  return [
    `Geladene Basisdatenfelder: ${present.length ? present.join(', ') : 'keine'}`,
    `Auto-Gates: ${Object.entries(gates).map(([k, v]) => `${k}=${v}`).join('; ')}`,
    `Auto-Scores: ${Object.entries(scores).map(([k, v]) => `${k}=${v}`).join('; ')}`,
    `Offene Punkte: ${openGates.length ? openGates.join(', ') : 'keine'}`
  ].join('\n');
}

export function mergeBaseDataIntoForm(currentFormData, normalizedData, autoGates, autoScores, autoNote) {
  return { ...currentFormData, ...normalizedData, ...autoGates, ...autoScores, autoDataStatus: 'Fallback-Import genutzt (kein Live-Provider)', autoDataNote: autoNote, baseDataJson: JSON.stringify(normalizedData, null, 2) };
}

export function getResearchJsonSchema() {
  return {
    asset: { ticker: '', isin: '', wkn: '', name: '', assetType: '' },
    qualitative_gates: {
      edge_proof: { status: 'PASS|FAIL|OFFEN', reason: '', evidence: [] },
      governance: { status: 'PASS|FAIL|OFFEN', reason: '', evidence: [] }
    },
    qualitative_scores: { edge_strength_override: { value: 0, max: 30, reason: '' } },
    summary: { thesis: '', catalyst: '', risks: '', management_quality: '', regulatory_context: '' },
    optional_overrides: { gateRunwayStatus: null, gateGrowthConvexityStatus: null, scoreQuality: null, scoreGrowthLeverage: null, scoreSatelliteFit: null }
  };
}

export function buildResearchPrompt(formData) {
  const schema = JSON.stringify(getResearchJsonSchema(), null, 2);
  return `Du bist ein Equity/ETF-Research-Agent. Analysiere nur qualitative/offene Punkte und respektiere die quantitative Vorbewertung.

Asset-Identifier:
- ticker: ${formData.ticker || ''}
- isin: ${formData.isin || ''}
- wkn: ${formData.wkn || ''}
- companyName: ${formData.companyName || ''}
- assetType: ${formData.assetType || ''}
- analysisType: ${formData.analysisType || ''}

Wichtig:
- Quantitative Daten nicht raten.
- Nur qualitative/offene Punkte ergänzen.
- Antwort ausschließlich als valides JSON.

Schema:
${schema}`;
}

const normalizeStatus = (v) => (typeof v === 'string' && VALID_GATE_STATUS.has(v.toUpperCase()) ? v.toUpperCase() : null);
const normalizeBoundedNumber = (v, min, max) => {
  const n = Number(v);
  if (!Number.isFinite(n) || n < min || n > max) return null;
  return n;
};

export function parseAndMapResearchJson(jsonText, currentFormData) {
  const parsed = JSON.parse(jsonText);
  const updates = { researchJson: JSON.stringify(parsed, null, 2) };

  const edge = parsed?.qualitative_gates?.edge_proof;
  const gov = parsed?.qualitative_gates?.governance;
  const edgeStatus = normalizeStatus(edge?.status);
  const govStatus = normalizeStatus(gov?.status);
  if (edgeStatus) updates.gateEdgeProof = edgeStatus;
  if (govStatus) updates.gateGovernance = govStatus;

  const edgeValue = normalizeBoundedNumber(parsed?.qualitative_scores?.edge_strength_override?.value, 0, 30);
  if (edgeValue !== null) updates.scoreEdgeStrength = edgeValue;

  if (parsed?.summary?.thesis) updates.thesis = parsed.summary.thesis;
  if (parsed?.summary?.catalyst) updates.catalyst = parsed.summary.catalyst;
  if (parsed?.summary?.risks) updates.risk = parsed.summary.risks;

  const extraSummary = [parsed?.summary?.management_quality, parsed?.summary?.regulatory_context].filter(Boolean).join('\n\n');
  if (extraSummary) updates.summary = [currentFormData.summary, extraSummary].filter(Boolean).join('\n\n');

  const runway = normalizeStatus(parsed?.optional_overrides?.gateRunwayStatus);
  const growth = normalizeStatus(parsed?.optional_overrides?.gateGrowthConvexityStatus);
  if (runway) updates.gateRunway = runway;
  if (growth) updates.gateGrowthConvexity = growth;

  const sq = normalizeBoundedNumber(parsed?.optional_overrides?.scoreQuality, 0, 25);
  const sg = normalizeBoundedNumber(parsed?.optional_overrides?.scoreGrowthLeverage, 0, 25);
  const ss = normalizeBoundedNumber(parsed?.optional_overrides?.scoreSatelliteFit, 0, 20);
  if (sq !== null) updates.scoreQuality = sq;
  if (sg !== null) updates.scoreGrowthLeverage = sg;
  if (ss !== null) updates.scoreSatelliteFit = ss;

  const gateNotes = [edge?.reason ? `Edge-Proof: ${edge.reason}` : '', gov?.reason ? `Governance: ${gov.reason}` : ''].filter(Boolean).join('\n');
  if (gateNotes) updates.gateNotes = [currentFormData.gateNotes, gateNotes].filter(Boolean).join('\n');

  const edgeReason = parsed?.qualitative_scores?.edge_strength_override?.reason;
  if (edgeReason) updates.scoreNotes = [currentFormData.scoreNotes, `Edge-Stärke Override: ${edgeReason}`].filter(Boolean).join('\n');

  return updates;
}
