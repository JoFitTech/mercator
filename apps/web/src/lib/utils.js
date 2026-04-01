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

const appendSection = (existing, title, content) => {
  const normalizedContent = asText(content);
  if (!normalizedContent) return existing || '';
  const section = `[${title}]\n${normalizedContent}`;
  return [existing, section].filter(Boolean).join('\n\n');
};

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

  let hardViolations = 0;
  if (exchangeKnown && exchangeAllowed === false) hardViolations += 1;
  if (mcap !== null && mcap < 1e9) hardViolations += 1;
  if (vol !== null && vol < 1e7) hardViolations += 1;
  if (spread !== null && spread > 0.3) hardViolations += 1;

  if (exchangeAllowed && mcap >= 1e9 && vol >= 1e7 && spread <= 0.3) gates.gateUniverseLiquidityStatus = 'PASS';
  else if (hardViolations >= 2) gates.gateUniverseLiquidityStatus = 'FAIL';
  else gates.gateUniverseLiquidityStatus = 'OFFEN';

  if (data.netCashFlag === true || (data.ttmFcf !== null && data.ttmFcf > 0) || (data.runwayMonths !== null && data.runwayMonths >= 18)) {
    gates.gateRunwayStatus = 'PASS';
  } else {
    gates.gateRunwayStatus = 'OFFEN';
  }

  gates.gateEdgeProofStatus = 'OFFEN';

  if (data.revenueCagr3y !== null && data.revenueCagr3y >= 10 && ['stabil', 'verbessernd', 'improving'].includes(data.marginTrend)) {
    gates.gateGrowthConvexityStatus = 'PASS';
  } else if (data.revenueCagr3y !== null && data.revenueCagr3y < 0 && ['verschlechternd', 'deteriorating'].includes(data.marginTrend)) {
    gates.gateGrowthConvexityStatus = 'FAIL';
  } else {
    gates.gateGrowthConvexityStatus = 'OFFEN';
  }

  gates.gateGovernanceStatus = 'OFFEN';

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
  const scores = { scoreEdgeStrength: 0, scoreQuality: 0, scoreGrowthLeverage: 0, scoreSatelliteFit: 0 };
  const notes = [];

  notes.push('Edge-Stärke bleibt automatisch auf 0 (qualitatives Research erforderlich).');

  if (data.ttmFcf !== null) {
    if (data.ttmFcf > 0) scores.scoreQuality += 10;
    else scores.scoreQuality += 2;
  } else {
    notes.push('ttmFcf fehlt -> Qualitäts-Score nur teilweise ableitbar.');
  }
  if (data.netCashFlag === true) scores.scoreQuality += 10;
  else if (data.netCashFlag === false) scores.scoreQuality += 2;
  else notes.push('netCashFlag fehlt -> Qualitäts-Score konservativ.');

  if (data.dilutionTrend === 'niedrig' || data.dilutionTrend === 'fallend') scores.scoreQuality += 5;
  else if (data.dilutionTrend === 'stabil') scores.scoreQuality += 3;
  else if (data.dilutionTrend) scores.scoreQuality += 1;
  else notes.push('dilutionTrend fehlt -> Qualitäts-Score konservativ.');
  scores.scoreQuality = Math.min(scores.scoreQuality, 25);

  if (data.revenueCagr3y !== null) {
    if (data.revenueCagr3y >= 20) scores.scoreGrowthLeverage += 15;
    else if (data.revenueCagr3y >= 10) scores.scoreGrowthLeverage += 10;
    else if (data.revenueCagr3y >= 5) scores.scoreGrowthLeverage += 6;
    else if (data.revenueCagr3y >= 0) scores.scoreGrowthLeverage += 3;
  } else {
    notes.push('revenueCagr3y fehlt -> Growth-Score konservativ.');
  }
  if (data.marginTrend === 'verbessernd' || data.marginTrend === 'improving') scores.scoreGrowthLeverage += 10;
  else if (data.marginTrend === 'stabil') scores.scoreGrowthLeverage += 6;
  else if (data.marginTrend === 'verschlechternd' || data.marginTrend === 'deteriorating') scores.scoreGrowthLeverage += 1;
  else notes.push('marginTrend fehlt -> Growth-Score konservativ.');
  scores.scoreGrowthLeverage = Math.min(scores.scoreGrowthLeverage, 25);

  if (data.avgDollarVolume !== null) {
    if (data.avgDollarVolume >= 5e7) scores.scoreSatelliteFit += 8;
    else if (data.avgDollarVolume >= 1e7) scores.scoreSatelliteFit += 5;
    else scores.scoreSatelliteFit += 1;
  } else {
    notes.push('avgDollarVolume fehlt -> Satellite-Fit nur teilweise ableitbar.');
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

export function mergeBaseDataIntoForm(currentFormData, normalizedData, autoGates, autoScores, autoNote) {
  const updates = {
    ...autoGates,
    ...autoScores,
    autoDataStatus: 'Fallback-Import genutzt (kein Live-Provider)',
    autoDataNote: autoNote
  };

  if (normalizedData.ticker) updates.ticker = normalizedData.ticker;
  if (normalizedData.companyName) updates.companyName = normalizedData.companyName;
  if (['Aktie', 'ETF', 'Pennystock'].includes(normalizedData.assetType)) updates.assetType = normalizedData.assetType;

  updates.gateNotes = appendSection(currentFormData.gateNotes, 'AUTO_GATE_IMPORT', [
    `exchange=${normalizedData.exchange || 'n/a'}`,
    `marketCap=${normalizedData.marketCap ?? 'n/a'}`,
    `avgDollarVolume=${normalizedData.avgDollarVolume ?? 'n/a'}`,
    `spreadPct=${normalizedData.spreadPct ?? 'n/a'}`,
    `daysToEarnings=${normalizedData.daysToEarnings ?? 'n/a'}`,
    `runwayMonths=${normalizedData.runwayMonths ?? 'n/a'}`,
    `ttmFcf=${normalizedData.ttmFcf ?? 'n/a'}`
  ].join('; '));

  updates.scoreNotes = appendSection(currentFormData.scoreNotes, 'AUTO_SCORE_IMPORT', [
    `scoreEdgeStrength=${autoScores.scoreEdgeStrength}`,
    `scoreQuality=${autoScores.scoreQuality}`,
    `scoreGrowthLeverage=${autoScores.scoreGrowthLeverage}`,
    `scoreSatelliteFit=${autoScores.scoreSatelliteFit}`,
    'Edge-Stärke bleibt ohne qualitative Evidenz offen.'
  ].join('; '));

  return { ...currentFormData, ...updates };
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

Bereits vorhandene quantitative Vorbefüllung:
- gateUniverseLiquidityStatus=${formData.gateUniverseLiquidityStatus}
- gateRunwayStatus=${formData.gateRunwayStatus}
- gateEdgeProofStatus=${formData.gateEdgeProofStatus}
- gateGrowthConvexityStatus=${formData.gateGrowthConvexityStatus}
- gateGovernanceStatus=${formData.gateGovernanceStatus}
- gateTradingFeasibilityStatus=${formData.gateTradingFeasibilityStatus}
- scoreEdgeStrength=${formData.scoreEdgeStrength}
- scoreQuality=${formData.scoreQuality}
- scoreGrowthLeverage=${formData.scoreGrowthLeverage}
- scoreSatelliteFit=${formData.scoreSatelliteFit}

Anweisungen:
1) Keine quantitativen Daten raten oder erfinden.
2) Nur qualitative Lücken recherchieren und bewerten.
3) Fokus auf Edge-Proof, Governance, Management-Qualität, Regulatorik, Bottleneck/Switching Costs/Netzwerk, These, Katalysator, Risiko.
4) Gib ausschließlich valides JSON gemäß Schema aus.

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
  const updates = {};

  const edge = parsed?.qualitative_gates?.edge_proof;
  const gov = parsed?.qualitative_gates?.governance;
  const edgeStatus = normalizeStatus(edge?.status);
  const govStatus = normalizeStatus(gov?.status);
  if (edgeStatus) updates.gateEdgeProofStatus = edgeStatus;
  if (govStatus) updates.gateGovernanceStatus = govStatus;

  const edgeValue = normalizeBoundedNumber(parsed?.qualitative_scores?.edge_strength_override?.value, 0, 30);
  if (edgeValue !== null) updates.scoreEdgeStrength = edgeValue;

  if (parsed?.summary?.thesis) updates.thesis = parsed.summary.thesis;
  if (parsed?.summary?.catalyst) updates.catalyst = parsed.summary.catalyst;
  if (parsed?.summary?.risks) updates.risk = parsed.summary.risks;

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

  const edgeEvidence = Array.isArray(edge?.evidence) ? edge.evidence.join(' | ') : '';
  const govEvidence = Array.isArray(gov?.evidence) ? gov.evidence.join(' | ') : '';
  const gateNotePayload = [
    edge?.reason ? `Edge-Proof Reason: ${edge.reason}` : '',
    edgeEvidence ? `Edge-Proof Evidence: ${edgeEvidence}` : '',
    gov?.reason ? `Governance Reason: ${gov.reason}` : '',
    govEvidence ? `Governance Evidence: ${govEvidence}` : '',
    parsed?.summary?.management_quality ? `Management-Qualität: ${parsed.summary.management_quality}` : '',
    parsed?.summary?.regulatory_context ? `Regulatorik: ${parsed.summary.regulatory_context}` : ''
  ]
    .filter(Boolean)
    .join('\n');

  if (gateNotePayload) updates.gateNotes = appendSection(currentFormData.gateNotes, 'AI_RESEARCH_GATE_UPDATE', gateNotePayload);

  const edgeReason = parsed?.qualitative_scores?.edge_strength_override?.reason;
  if (edgeReason) {
    updates.scoreNotes = appendSection(currentFormData.scoreNotes, 'AI_RESEARCH_SCORE_UPDATE', `Edge-Stärke Override: ${edgeReason}`);
  }

  return updates;
}
