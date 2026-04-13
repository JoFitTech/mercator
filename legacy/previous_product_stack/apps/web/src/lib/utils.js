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

export function stripMetaBlock(rawText) {
  return splitMetaNotes(rawText).visibleText || '';
}

export function mergeVisibleNotesWithMeta(visibleText, metaObj) {
  const visible = asText(visibleText);
  const metaPayload = metaObj && typeof metaObj === 'object' ? metaObj : {};

  const hasMeta = Object.values(metaPayload).some((v) => v !== '' && v !== null && v !== undefined);
  if (!hasMeta) return visible;

  const metaJson = JSON.stringify(metaPayload, null, 2);
  return [visible, FP_META_START, metaJson, FP_META_END].filter(Boolean).join('\n\n');
}

export function buildMetaBlock(metaObj = {}) {
  const metaPayload = metaObj && typeof metaObj === 'object' ? metaObj : {};
  const hasMeta = Object.values(metaPayload).some((v) => v !== '' && v !== null && v !== undefined);
  if (!hasMeta) return '';
  return [FP_META_START, JSON.stringify(metaPayload, null, 2), FP_META_END].join('\n');
}

export function mergeVisibleTextWithMeta(visibleText, metaObj) {
  const visible = asText(visibleText);
  const metaBlock = buildMetaBlock(metaObj);
  if (!metaBlock) return visible;
  return [visible, metaBlock].filter(Boolean).join('\n\n');
}

// Legacy alias for compatibility with existing imports/components.
export function buildMetaBlockLegacy(visibleText, metaObj) {
  return mergeVisibleTextWithMeta(visibleText, metaObj);
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
    asset: { ticker: '', isin: '', wkn: '', name: '', assetType: '', analysisType: '' },
    gates: {
      universe_liquidity: { status: 'PASS|FAIL|OFFEN', reason: '', evidence: [] },
      runway_18_24m: { status: 'PASS|FAIL|OFFEN', reason: '', evidence: [] },
      edge_proof: { status: 'PASS|FAIL|OFFEN', reason: '', evidence: [] },
      growth_convexity: { status: 'PASS|FAIL|OFFEN', reason: '', evidence: [] },
      governance: { status: 'PASS|FAIL|OFFEN', reason: '', evidence: [] },
      trading_feasibility: { status: 'PASS|FAIL|OFFEN', reason: '', evidence: [] }
    },
    scores: {
      edge_strength: { value: 0, max: 30, reason: '' },
      quality: { value: 0, max: 25, reason: '' },
      growth_leverage: { value: 0, max: 25, reason: '' },
      satellite_fit: { value: 0, max: 20, reason: '' }
    },
    summary: { thesis: '', summary: '', catalyst: '', risks: '', management_quality: '', regulatory_context: '' },
    result: { final_score: 0, decision_bucket: 'kein Kandidat|Watchlist|Kaufkandidat|Booster-Kandidat', final_decision: 'kein Kandidat|Watchlist|Kaufkandidat|Booster-Kandidat|Ausschluss' }
  };
}

export function buildResearchPrompt({ identifiers, analysisType, formData, formatPreference = 'JSON' }) {
  const schema = JSON.stringify(getResearchJsonSchema(), null, 2);
  const optionalFormatHint = formatPreference !== 'JSON'
    ? `\nBevorzugtes Antwortformat: ${formatPreference}\nWichtig: Der Import in dieser App unterstützt in dieser Version zuverlässig nur JSON.\n`
    : '';
  return `Du bist ein Equity/ETF-Research-Agent für eine strukturierte Hybrid-Analyse nach Satellite-Checkliste.

Asset-Kontext:
- ticker: ${identifiers.ticker || formData.ticker || ''}
- isin: ${identifiers.isin || ''}
- wkn: ${identifiers.wkn || ''}
- companyName: ${formData.companyName || ''}
- assetType: ${formData.assetType || ''}
- analysisType: ${analysisType || 'nicht gesetzt'}

Ziel:
- Standardisierte Analyse für Mercator.
- Fokus auf Hard Gates, Score-Blöcke, These, Katalysator, Risiko, Management und Regulatorik.

Harte Regeln:
1) Keine quantitativen Daten raten.
2) Keine qualitativen Aussagen ohne Begründung.
3) Nur belastbare Quellen und Unsicherheit explizit markieren.
4) Kein Fließtext außerhalb des gewünschten Formats.
5) Wenn Daten fehlen: Status OFFEN setzen statt zu halluzinieren.
6) Bei ETF ETF-spezifische Logik anwenden, bei Aktie/Pennystock primär Satellite-Checkliste.

Fachliche Bewertungslogik:
1. Universum & Liquidität
2. Runway 18-24M
3. Edge-Proof
4. Wachstum/Konvexität
5. Governance
6. Trading-Feasibility
Scoring: Edge-Stärke /30, Qualität /25, Wachstum & Leverage /25, Satellite-Fit /20.
Schwellen: <75 kein Kandidat, 75-84 Watchlist, 85-89 Kaufkandidat, >=90 Booster-Kandidat, irgendein Gate FAIL = Ausschluss.

Was konkret recherchiert werden soll:
- Universe/Liquidity Daten
- Runway / Net Cash / FCF / Refinanzierungsrisiko
- Edge-Proof mit mindestens zwei Proxies
- Wachstum / Konvexität / Trendverbesserung
- Governance / Red Flags
- Trading-Feasibility
- Qualitätsmerkmale
- Wachstum & Leverage
- Satellite-Fit
- Investment-These
- Katalysator
- Risiko
- Management-Qualität
- Regulatorik-Kontext

Ausgabeformat:
- Primär JSON, kein zusätzlicher Text davor oder danach.
${optionalFormatHint}

Schema:
${schema}`;
}

export function parseResearchJson(jsonText) {
  const parsed = JSON.parse(jsonText);
  const updates = {};
  const gateNotes = [];
  const scoreNotes = [];

  const gateMap = [
    ['universe_liquidity', 'gateUniverseLiquidityStatus', 'Universum & Liquidität'],
    ['runway_18_24m', 'gateRunwayStatus', 'Runway 18-24M'],
    ['edge_proof', 'gateEdgeProofStatus', 'Edge-Proof'],
    ['growth_convexity', 'gateGrowthConvexityStatus', 'Wachstum/Konvexität'],
    ['governance', 'gateGovernanceStatus', 'Governance'],
    ['trading_feasibility', 'gateTradingFeasibilityStatus', 'Trading-Feasibility']
  ];

  gateMap.forEach(([sourceKey, targetKey, label]) => {
    const gateItem = parsed?.gates?.[sourceKey];
    const status = normalizeStatus(gateItem?.status);
    if (status) updates[targetKey] = status;
    if (gateItem?.reason) gateNotes.push(`${label}: ${gateItem.reason}`);
    if (Array.isArray(gateItem?.evidence) && gateItem.evidence.length) {
      gateNotes.push(`${label} Evidenz: ${gateItem.evidence.join(' | ')}`);
    }
  });

  const scoreMap = [
    ['edge_strength', 'scoreEdgeStrength', 30, 'Edge-Stärke'],
    ['quality', 'scoreQuality', 25, 'Qualität'],
    ['growth_leverage', 'scoreGrowthLeverage', 25, 'Wachstum & Leverage'],
    ['satellite_fit', 'scoreSatelliteFit', 20, 'Satellite-Fit']
  ];

  scoreMap.forEach(([sourceKey, targetKey, max, label]) => {
    const scoreItem = parsed?.scores?.[sourceKey];
    const value = normalizeBoundedNumber(scoreItem?.value, 0, max);
    if (value !== null) updates[targetKey] = value;
    if (scoreItem?.reason) scoreNotes.push(`${label}: ${scoreItem.reason}`);
  });

  if (parsed?.summary?.thesis) updates.thesis = parsed.summary.thesis;
  if (parsed?.summary?.summary) updates.summary = parsed.summary.summary;
  if (parsed?.summary?.catalyst) updates.catalyst = parsed.summary.catalyst;
  if (parsed?.summary?.risks) updates.risk = parsed.summary.risks;

  if (parsed?.summary?.management_quality) gateNotes.push(`Management-Qualität: ${parsed.summary.management_quality}`);
  if (parsed?.summary?.regulatory_context) gateNotes.push(`Regulatorik-Kontext: ${parsed.summary.regulatory_context}`);

  return { parsed, updates, gateNotes, scoreNotes };
}
