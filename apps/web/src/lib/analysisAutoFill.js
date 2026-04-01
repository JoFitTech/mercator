const ALLOWED_EXCHANGES = new Set(['NYSE', 'NASDAQ', 'XETRA', 'EURONEXT', 'LSE', 'TSX', 'SIX']);

const EXCHANGE_ALIASES = {
  XETR: 'XETRA',
  XETRA: 'XETRA',
  NASDAQGS: 'NASDAQ',
  NASDAQGM: 'NASDAQ',
  NYSEARCA: 'NYSE',
  ENX: 'EURONEXT'
};

const STATUS = {
  PASS: 'PASS',
  FAIL: 'FAIL',
  OPEN: 'OFFEN'
};

const num = (v) => {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

const bool = (v) => {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'number') return v !== 0;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    if (['true', 'ja', 'yes', '1'].includes(s)) return true;
    if (['false', 'nein', 'no', '0'].includes(s)) return false;
  }
  return null;
};

const text = (v) => (v === null || v === undefined ? '' : String(v).trim());

const normalizeExchange = (value) => {
  const raw = text(value).toUpperCase();
  if (!raw) return '';
  return EXCHANGE_ALIASES[raw] || raw;
};

const normalizeAssetType = (value) => {
  const raw = text(value).toLowerCase();
  if (!raw) return '';
  if (['etf', 'fonds'].includes(raw)) return 'ETF';
  if (['aktie', 'stock', 'equity'].includes(raw)) return 'Aktie';
  if (['pennystock', 'penny stock'].includes(raw)) return 'Pennystock';
  return text(value);
};

export function normalizeIdentifierInput({ isin, wkn, ticker }) {
  const normalized = {
    isin: text(isin).toUpperCase(),
    wkn: text(wkn).toUpperCase(),
    ticker: text(ticker).toUpperCase()
  };

  const lookup = normalized.isin || normalized.wkn || normalized.ticker;
  const lookupType = normalized.isin ? 'isin' : normalized.wkn ? 'wkn' : normalized.ticker ? 'ticker' : '';

  return { ...normalized, lookup, lookupType };
}

export function normalizeBaseData(raw = {}) {
  return {
    ticker: text(raw.ticker || raw.symbol).toUpperCase(),
    companyName: text(raw.companyName || raw.name),
    assetType: normalizeAssetType(raw.assetType || raw.type),
    isin: text(raw.isin).toUpperCase(),
    wkn: text(raw.wkn).toUpperCase(),
    exchange: normalizeExchange(raw.exchange),
    country: text(raw.country),
    region: text(raw.region),
    sector: text(raw.sector),
    currency: text(raw.currency || raw.ccy).toUpperCase(),
    price: num(raw.price),
    marketCap: num(raw.marketCap),
    avgDollarVolume: num(raw.avgDollarVolume),
    spreadPct: num(raw.spreadPct),
    earningsDate: text(raw.earningsDate),
    daysToEarnings: num(raw.daysToEarnings),
    ttmFcf: num(raw.ttmFcf),
    netCashFlag: bool(raw.netCashFlag),
    runwayMonths: num(raw.runwayMonths),
    revenueCagr3y: num(raw.revenueCagr3y),
    marginTrend: text(raw.marginTrend).toLowerCase(),
    dilutionTrend: text(raw.dilutionTrend).toLowerCase(),
    volatilityBucket: text(raw.volatilityBucket).toLowerCase(),
    terPct: num(raw.terPct),
    domicile: text(raw.domicile),
    replicationMethod: text(raw.replicationMethod),
    trackingDifferencePct: num(raw.trackingDifferencePct)
  };
}

export function deriveAutoGates(data) {
  const gates = {};
  const notes = [];

  const exchangeKnown = Boolean(data.exchange);
  const exchangeAllowed = exchangeKnown ? ALLOWED_EXCHANGES.has(data.exchange) : null;
  const mcap = data.marketCap;
  const vol = data.avgDollarVolume;
  const spread = data.spreadPct;

  let hardViolations = 0;
  if (mcap !== null && mcap < 1e9) hardViolations += 1;
  if (vol !== null && vol < 1e7) hardViolations += 1;
  if (spread !== null && spread > 0.3) hardViolations += 1;

  if (exchangeKnown && exchangeAllowed === false) {
    gates.gateUniverseLiquidity = STATUS.FAIL;
    notes.push('Gate 1 FAIL: Börse ist außerhalb des erlaubten Universums.');
  } else if (hardViolations >= 2) {
    gates.gateUniverseLiquidity = STATUS.FAIL;
    notes.push('Gate 1 FAIL: Mindestens zwei harte Liquiditäts-Schwellen verletzt.');
  } else if (exchangeAllowed && mcap >= 1e9 && vol >= 1e7 && spread <= 0.3) {
    gates.gateUniverseLiquidity = STATUS.PASS;
    notes.push('Gate 1 PASS: Börse, Market Cap, Volumen und Spread erfüllen die Schwellen.');
  } else {
    gates.gateUniverseLiquidity = STATUS.OPEN;
    notes.push('Gate 1 OFFEN: Für Universum/Liquidität fehlen Daten oder Kriterien sind nicht vollständig.');
  }

  if (data.netCashFlag === true || (data.ttmFcf !== null && data.ttmFcf > 0) || (data.runwayMonths !== null && data.runwayMonths >= 18)) {
    gates.gateRunway = STATUS.PASS;
    notes.push('Gate 2 PASS: Runway durch Net Cash, positiven FCF oder >=18 Monate abgedeckt.');
  } else {
    gates.gateRunway = STATUS.OPEN;
    notes.push('Gate 2 OFFEN: Runway nicht klar beurteilbar.');
  }

  gates.gateEdgeProof = STATUS.OPEN;
  notes.push('Gate 3 OFFEN: Edge-Proof benötigt qualitative Recherche.');

  const growthKnown = data.revenueCagr3y !== null;
  const marginKnown = Boolean(data.marginTrend);
  const marginGood = ['stabil', 'verbessernd'].includes(data.marginTrend);
  const marginBad = ['verschlechternd'].includes(data.marginTrend);

  if (growthKnown && marginKnown && data.revenueCagr3y >= 10 && marginGood) {
    gates.gateGrowthConvexity = STATUS.PASS;
    notes.push('Gate 4 PASS: Wachstum >=10% und Margin-Trend stabil/verbessernd.');
  } else if (growthKnown && marginKnown && data.revenueCagr3y < 5 && marginBad) {
    gates.gateGrowthConvexity = STATUS.FAIL;
    notes.push('Gate 4 FAIL: Klar negatives Wachstum/Margenbild.');
  } else {
    gates.gateGrowthConvexity = STATUS.OPEN;
    notes.push('Gate 4 OFFEN: Wachstum/Konvexität nicht eindeutig.');
  }

  gates.gateGovernance = STATUS.OPEN;
  notes.push('Gate 5 OFFEN: Governance benötigt qualitative Recherche.');

  const dte = data.daysToEarnings;
  if ((dte !== null && dte < 7) || (vol !== null && vol < 1e7) || (spread !== null && spread > 0.3)) {
    gates.gateTradingFeasibility = STATUS.FAIL;
    notes.push('Gate 6 FAIL: Trading-Feasibility verletzt (Earnings/Volumen/Spread).');
  } else if (vol !== null && spread !== null && vol >= 1e7 && spread <= 0.3 && (dte === null || dte >= 7)) {
    gates.gateTradingFeasibility = STATUS.PASS;
    notes.push('Gate 6 PASS: Trading-Feasibility erfüllt (Volumen, Spread, Earnings-Puffer).');
  } else {
    gates.gateTradingFeasibility = STATUS.OPEN;
    notes.push('Gate 6 OFFEN: Trading-Feasibility nicht vollständig bestimmbar.');
  }

  return { gates, notes };
}

export function deriveAutoScores(data) {
  const notes = [];
  const scores = { scoreEdgeStrength: 0, scoreQuality: 0, scoreGrowthLeverage: 0, scoreSatelliteFit: 0 };

  notes.push('Edge-Stärke: nicht automatisch ableitbar (0/30, qualitative Validierung erforderlich).');

  let quality = 0;
  if (data.ttmFcf !== null) quality += data.ttmFcf > 0 ? 10 : 0;
  else notes.push('Qualität: TTM FCF fehlt.');
  if (data.netCashFlag !== null) quality += data.netCashFlag ? 10 : 0;
  else notes.push('Qualität: NetCash-Flag fehlt.');
  if (data.dilutionTrend) {
    if (data.dilutionTrend === 'niedrig') quality += 5;
    if (data.dilutionTrend === 'stabil') quality += 3;
  } else {
    notes.push('Qualität: Dilution-Trend fehlt.');
  }
  scores.scoreQuality = Math.min(25, quality);

  let growth = 0;
  if (data.revenueCagr3y !== null) {
    if (data.revenueCagr3y >= 20) growth += 15;
    else if (data.revenueCagr3y >= 10) growth += 10;
    else if (data.revenueCagr3y >= 5) growth += 5;
  } else {
    notes.push('Wachstum: Revenue CAGR 3Y fehlt.');
  }
  if (data.marginTrend) {
    if (data.marginTrend === 'verbessernd') growth += 10;
    else if (data.marginTrend === 'stabil') growth += 6;
  } else {
    notes.push('Wachstum: Margin-Trend fehlt.');
  }
  scores.scoreGrowthLeverage = Math.min(25, growth);

  let satellite = 0;
  if (data.avgDollarVolume !== null) {
    if (data.avgDollarVolume >= 5e7) satellite += 8;
    else if (data.avgDollarVolume >= 1e7) satellite += 5;
  } else notes.push('Satellite-Fit: Volumen fehlt.');

  if (data.spreadPct !== null) {
    if (data.spreadPct <= 0.1) satellite += 6;
    else if (data.spreadPct <= 0.3) satellite += 3;
  } else notes.push('Satellite-Fit: Spread fehlt.');

  if (data.volatilityBucket) {
    if (['niedrig', 'low'].includes(data.volatilityBucket)) satellite += 6;
    else if (['mittel', 'medium'].includes(data.volatilityBucket)) satellite += 4;
    else satellite += 2;
  } else notes.push('Satellite-Fit: Volatility-Bucket fehlt.');

  if (data.daysToEarnings !== null && data.daysToEarnings < 7) satellite = Math.max(0, satellite - 2);

  scores.scoreSatelliteFit = Math.min(20, satellite);

  return { scores, notes };
}

export function buildAutoDataNote({ normalizedData, gates, scores }) {
  const present = Object.entries(normalizedData)
    .filter(([, value]) => value !== '' && value !== null)
    .map(([key]) => key);

  const openGates = Object.entries(gates).filter(([, value]) => value === STATUS.OPEN).map(([key]) => key);

  return [
    `Geladene Basisdatenfelder: ${present.length ? present.join(', ') : 'keine'}`,
    `Auto-Gates: ${Object.entries(gates).map(([k, v]) => `${k}=${v}`).join('; ')}`,
    `Auto-Scores: ${Object.entries(scores).map(([k, v]) => `${k}=${v}`).join('; ')}`,
    openGates.length ? `Offene Punkte (qualitativ/fehlende Daten): ${openGates.join(', ')}` : 'Keine offenen Gate-Punkte.'
  ].join('\n');
}

export function mergeBaseDataIntoForm(currentFormData, normalizedData, autoGates, autoScores, autoNote) {
  return {
    ...currentFormData,
    ...normalizedData,
    ...autoGates,
    ...autoScores,
    autoDataStatus: 'Fallback-Import genutzt (kein Live-Provider)',
    autoDataNote: autoNote,
    baseDataJson: JSON.stringify(normalizedData, null, 2)
  };
}
