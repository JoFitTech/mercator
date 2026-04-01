import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const ALLOWED_EXCHANGES = new Set(['NYSE', 'NASDAQ', 'XETRA', 'EURONEXT', 'LSE', 'TSX', 'SIX']);
const EXCHANGE_ALIASES = { XETR: 'XETRA', XETRA: 'XETRA', NASDAQGS: 'NASDAQ', NASDAQGM: 'NASDAQ', NYSEARCA: 'NYSE', ENX: 'EURONEXT' };
const VALID_GATE_STATUS = new Set(['PASS', 'FAIL', 'OFFEN']);

const FP_META_START = '[[FP_META]]';
const FP_META_END = '[[/FP_META]]';

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

const normalizeStatus = (v) => (typeof v === 'string' && VALID_GATE_STATUS.has(v.toUpperCase()) ? v.toUpperCase() : null);
const normalizeBoundedNumber = (v, min, max) => {
  const n = Number(v);
  if (!Number.isFinite(n) || n < min || n > max) return null;
  return n;
};

export function safeJsonParse(value, fallback = null) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

export function splitMetaNotes(rawText) {
  const text = asText(rawText);
  if (!text) return { visibleText: '', meta: {}, rawMeta: '' };

  const start = text.indexOf(FP_META_START);
  const end = text.indexOf(FP_META_END);

  if (start === -1 || end === -1 || end < start) {
    return { visibleText: text, meta: {}, rawMeta: '' };
  }

  const before = text.slice(0, start).trimEnd();
  const jsonText = text.slice(start + FP_META_START.length, end).trim();
  const meta = safeJsonParse(jsonText, {});

  return {
    visibleText: before,
    meta: meta && typeof meta === 'object' ? meta : {},
    rawMeta: jsonText
  };
}

export function parseMetaBlock(rawText) {
  return splitMetaNotes(rawText);
}

export function mergeVisibleNotesWithMeta(visibleText, metaObj) {
  const visible = asText(visibleText);
  const metaPayload = metaObj && typeof metaObj === 'object' ? metaObj : {};

  const hasMeta = Object.values(metaPayload).some((v) => v !== '' && v !== null && v !== undefined);
  if (!hasMeta) return visible;

  const metaJson = JSON.stringify(metaPayload, null, 2);
  return [visible, FP_META_START, metaJson, FP_META_END].filter(Boolean).join('\n\n');
}

export function buildMetaBlock(visibleText, metaObj) {
  return mergeVisibleNotesWithMeta(visibleText, metaObj);
}

export function normalizeIdentifierInput({ isin, wkn, ticker }) {
  const normalized = {
    isin: asText(isin).toUpperCase(),
    wkn: asText(wkn).toUpperCase(),
    ticker: asText(ticker).toUpperCase()
  };
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

  if (exchangeAllowed && mcap >= 1e9 && vol >= 1e7 && spread <= 0.3) gates.gateUniverseLiquidityStatus = 'PASS';
  else if ((exchangeKnown && exchangeAllowed === false) || (mcap !== null && mcap < 1e9) || (vol !== null && vol < 1e7) || (spread !== null && spread > 0.3)) {
    gates.gateUniverseLiquidityStatus = 'FAIL';
  }
  else gates.gateUniverseLiquidityStatus = 'OFFEN';

  if (data.netCashFlag === true || (data.ttmFcf !== null && data.ttmFcf > 0) || (data.runwayMonths !== null && data.runwayMonths >= 18)) {
    gates.gateRunwayStatus = 'PASS';
  } else {
    gates.gateRunwayStatus = 'OFFEN';
  }

  if (data.revenueCagr3y !== null && data.revenueCagr3y >= 10 && ['stabil', 'verbessernd', 'improving'].includes(data.marginTrend)) {
    gates.gateGrowthConvexityStatus = 'PASS';
  } else if (data.revenueCagr3y !== null && data.revenueCagr3y < -10 && ['verschlechternd', 'deteriorating'].includes(data.marginTrend)) {
    gates.gateGrowthConvexityStatus = 'FAIL';
  } else {
    gates.gateGrowthConvexityStatus = 'OFFEN';
  }

  if ((dte !== null && dte < 7) || (vol !== null && vol < 1e7) || (spread !== null && spread > 0.3)) {
    gates.gateTradingFeasibilityStatus = 'FAIL';
  } else if (vol !== null && vol >= 1e7 && spread !== null && spread <= 0.3 && (dte === null || dte >= 7)) {
    gates.gateTradingFeasibilityStatus = 'PASS';
  } else {
    gates.gateTradingFeasibilityStatus = 'OFFEN';
  }

  return { gates };
}

export function deriveAutoScores(data) {
  const scores = { scoreQuality: 0, scoreGrowthLeverage: 0, scoreSatelliteFit: 0 };
  const notes = [];

  if (data.ttmFcf !== null) scores.scoreQuality += data.ttmFcf > 0 ? 10 : 2;
  else notes.push('ttmFcf fehlt -> Qualität konservativ.');

  if (data.netCashFlag === true) scores.scoreQuality += 10;
  else if (data.netCashFlag === false) scores.scoreQuality += 2;
  else notes.push('netCashFlag fehlt -> Qualität konservativ.');

  if (['niedrig', 'fallend'].includes(data.dilutionTrend)) scores.scoreQuality += 5;
  else if (data.dilutionTrend === 'stabil') scores.scoreQuality += 3;
  else if (data.dilutionTrend) scores.scoreQuality += 1;
  else notes.push('dilutionTrend fehlt -> Qualität konservativ.');
  scores.scoreQuality = Math.min(scores.scoreQuality, 25);

  if (data.revenueCagr3y !== null) {
    if (data.revenueCagr3y >= 20) scores.scoreGrowthLeverage += 15;
    else if (data.revenueCagr3y >= 10) scores.scoreGrowthLeverage += 10;
    else if (data.revenueCagr3y >= 5) scores.scoreGrowthLeverage += 6;
    else if (data.revenueCagr3y >= 0) scores.scoreGrowthLeverage += 3;
  } else {
    notes.push('revenueCagr3y fehlt -> Wachstum konservativ.');
  }

  if (['verbessernd', 'improving'].includes(data.marginTrend)) scores.scoreGrowthLeverage += 10;
  else if (data.marginTrend === 'stabil') scores.scoreGrowthLeverage += 6;
  else if (['verschlechternd', 'deteriorating'].includes(data.marginTrend)) scores.scoreGrowthLeverage += 1;
  else notes.push('marginTrend fehlt -> Wachstum konservativ.');
  scores.scoreGrowthLeverage = Math.min(scores.scoreGrowthLeverage, 25);

  if (data.avgDollarVolume !== null) {
    if (data.avgDollarVolume >= 5e7) scores.scoreSatelliteFit += 8;
    else if (data.avgDollarVolume >= 1e7) scores.scoreSatelliteFit += 5;
    else scores.scoreSatelliteFit += 1;
  } else {
    notes.push('avgDollarVolume fehlt -> Satellite-Fit konservativ.');
  }

  if (data.spreadPct !== null) {
    if (data.spreadPct <= 0.1) scores.scoreSatelliteFit += 6;
    else if (data.spreadPct <= 0.3) scores.scoreSatelliteFit += 3;
    else scores.scoreSatelliteFit += 1;
  } else {
    notes.push('spreadPct fehlt -> Satellite-Fit konservativ.');
  }

  if (['niedrig', 'low'].includes(data.volatilityBucket)) scores.scoreSatelliteFit += 6;
  else if (['mittel', 'medium'].includes(data.volatilityBucket)) scores.scoreSatelliteFit += 4;
  else if (data.volatilityBucket) scores.scoreSatelliteFit += 2;

  if (data.daysToEarnings !== null && data.daysToEarnings < 7) scores.scoreSatelliteFit = Math.max(0, scores.scoreSatelliteFit - 2);
  scores.scoreSatelliteFit = Math.min(scores.scoreSatelliteFit, 20);

  return { scores, notes };
}

export function buildAutoDataNote({ normalizedData, gates, scores, notes = [] }) {
  const present = Object.entries(normalizedData)
    .filter(([, v]) => v !== '' && v !== null)
    .map(([k]) => k);

  return [
    `Geladene Basisdatenfelder: ${present.length ? present.join(', ') : 'keine'}`,
    `Auto-Gates: ${Object.entries(gates).map(([k, v]) => `${k}=${v}`).join('; ')}`,
    `Auto-Scores: ${Object.entries(scores).map(([k, v]) => `${k}=${v}`).join('; ')}`,
    notes.length ? `Hinweise: ${notes.join(' | ')}` : ''
  ]
    .filter(Boolean)
    .join('\n');
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
    optional_overrides: {
      gateRunwayStatus: null,
      gateGrowthConvexityStatus: null,
      scoreQuality: null,
      scoreGrowthLeverage: null,
      scoreSatelliteFit: null
    }
  };
}

export function buildResearchPrompt({ identifiers, analysisType, formData }) {
  const schema = JSON.stringify(getResearchJsonSchema(), null, 2);
  return `Du bist ein Equity/ETF-Research-Agent für eine Hybrid-Analyse.

Asset-Kontext:
- ticker: ${identifiers.ticker || formData.ticker || ''}
- isin: ${identifiers.isin || ''}
- wkn: ${identifiers.wkn || ''}
- companyName: ${formData.companyName || ''}
- assetType: ${formData.assetType || ''}
- analysisType: ${analysisType || 'nicht gesetzt'}

Bereits gesetzte quantitative Gates:
- gateUniverseLiquidityStatus=${formData.gateUniverseLiquidityStatus}
- gateRunwayStatus=${formData.gateRunwayStatus}
- gateGrowthConvexityStatus=${formData.gateGrowthConvexityStatus}
- gateTradingFeasibilityStatus=${formData.gateTradingFeasibilityStatus}

Bereits gesetzte quantitative Scores:
- scoreQuality=${formData.scoreQuality}
- scoreGrowthLeverage=${formData.scoreGrowthLeverage}
- scoreSatelliteFit=${formData.scoreSatelliteFit}

Wichtige Regeln:
1) Quantitative Daten nicht raten oder erfinden.
2) Nur qualitative Lücken ergänzen.
3) Fokus: Edge-Proof, Governance, Management-Qualität, Regulatorik, Bottleneck/Switching Costs/Netzwerk, These, Katalysator, Risiko.
4) Edge-Stärke darf nur qualitativ begründet als Override geliefert werden.
5) Gib ausschließlich valides JSON gemäß Schema aus.

Schema:
${schema}`;
}

export function parseResearchJson(jsonText) {
  const parsed = JSON.parse(jsonText);
  const updates = {};
  const gateNotes = [];
  const scoreNotes = [];

  const edge = parsed?.qualitative_gates?.edge_proof;
  const gov = parsed?.qualitative_gates?.governance;
  const edgeStatus = normalizeStatus(edge?.status);
  const govStatus = normalizeStatus(gov?.status);
  if (edgeStatus) updates.gateEdgeProofStatus = edgeStatus;
  if (govStatus) updates.gateGovernanceStatus = govStatus;

  if (edge?.reason) gateNotes.push(`Edge-Proof: ${edge.reason}`);
  if (Array.isArray(edge?.evidence) && edge.evidence.length) gateNotes.push(`Edge-Evidence: ${edge.evidence.join(' | ')}`);
  if (gov?.reason) gateNotes.push(`Governance: ${gov.reason}`);
  if (Array.isArray(gov?.evidence) && gov.evidence.length) gateNotes.push(`Governance-Evidence: ${gov.evidence.join(' | ')}`);

  const edgeValue = normalizeBoundedNumber(parsed?.qualitative_scores?.edge_strength_override?.value, 0, 30);
  if (edgeValue !== null) updates.scoreEdgeStrength = edgeValue;
  if (parsed?.qualitative_scores?.edge_strength_override?.reason) {
    scoreNotes.push(`Edge-Override: ${parsed.qualitative_scores.edge_strength_override.reason}`);
  }

  if (parsed?.summary?.thesis) updates.thesis = parsed.summary.thesis;
  if (parsed?.summary?.catalyst) updates.catalyst = parsed.summary.catalyst;
  if (parsed?.summary?.risks) updates.risk = parsed.summary.risks;

  if (parsed?.summary?.management_quality) gateNotes.push(`Management-Qualität: ${parsed.summary.management_quality}`);
  if (parsed?.summary?.regulatory_context) gateNotes.push(`Regulatorik: ${parsed.summary.regulatory_context}`);

  const runway = normalizeStatus(parsed?.optional_overrides?.gateRunwayStatus);
  const growth = normalizeStatus(parsed?.optional_overrides?.gateGrowthConvexityStatus);
  if (runway) updates.gateRunwayStatus = runway;
  if (growth) updates.gateGrowthConvexityStatus = growth;

  const sq = normalizeBoundedNumber(parsed?.optional_overrides?.scoreQuality, 0, 25);
  const sg = normalizeBoundedNumber(parsed?.optional_overrides?.scoreGrowthLeverage, 0, 25);
  const ss = normalizeBoundedNumber(parsed?.optional_overrides?.scoreSatelliteFit, 0, 20);
  if (sq !== null) updates.scoreQuality = sq;
  if (sg !== null) updates.scoreGrowthLeverage = sg;
  if (ss !== null) updates.scoreSatelliteFit = ss;

  return { parsed, updates, gateNotes, scoreNotes };
}
