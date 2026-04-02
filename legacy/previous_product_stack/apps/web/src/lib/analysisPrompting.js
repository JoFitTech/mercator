const VALID_GATE_STATUS = new Set(['PASS', 'FAIL', 'OFFEN']);

export function getResearchJsonSchema() {
  return {
    asset: {
      ticker: '',
      isin: '',
      wkn: '',
      name: '',
      assetType: ''
    },
    qualitative_gates: {
      edge_proof: {
        status: 'PASS|FAIL|OFFEN',
        reason: '',
        evidence: []
      },
      governance: {
        status: 'PASS|FAIL|OFFEN',
        reason: '',
        evidence: []
      }
    },
    qualitative_scores: {
      edge_strength_override: {
        value: 0,
        max: 30,
        reason: ''
      }
    },
    summary: {
      thesis: '',
      catalyst: '',
      risks: '',
      management_quality: '',
      regulatory_context: ''
    },
    optional_overrides: {
      gateRunwayStatus: null,
      gateGrowthConvexityStatus: null,
      scoreQuality: null,
      scoreGrowthLeverage: null,
      scoreSatelliteFit: null
    }
  };
}

export function buildResearchPrompt(formData) {
  const schema = JSON.stringify(getResearchJsonSchema(), null, 2);

  return `Du bist ein Equity/ETF-Research-Agent. Analysiere NUR qualitative/offene Punkte und respektiere die bereits vorliegende quantitative Vorbewertung.

Asset-Identifier:
- ticker: ${formData.ticker || ''}
- isin: ${formData.isin || ''}
- wkn: ${formData.wkn || ''}
- companyName: ${formData.companyName || ''}
- assetType: ${formData.assetType || ''}
- analysisType: ${formData.analysisType || ''}

Bereits bekannte quantitative Vorbewertung (nicht überschreiben, außer optional_overrides bei klarer qualitativer Evidenz):
- gateUniverseLiquidity: ${formData.gateUniverseLiquidity}
- gateRunway: ${formData.gateRunway}
- gateGrowthConvexity: ${formData.gateGrowthConvexity}
- gateTradingFeasibility: ${formData.gateTradingFeasibility}
- scoreQuality: ${formData.scoreQuality}
- scoreGrowthLeverage: ${formData.scoreGrowthLeverage}
- scoreSatelliteFit: ${formData.scoreSatelliteFit}

Recherchefokus:
1) Edge-Proof (Bottleneck, Switching Costs, Netzwerkeffekte, Burggraben)
2) Governance & Management-Qualität
3) Regulatorik-Kontext
4) Investment-These, Katalysator, Hauptrisiken
5) Optional qualitative Einschätzung für Edge-Stärke (0-30)

WICHTIG:
- Keine quantitativen Daten raten oder erfinden.
- Wenn Evidenz unsicher ist, Status OFFEN verwenden.
- Antworten ausschließlich als valides JSON (ohne Markdown, ohne Zusatztext).
- Nutze exakt dieses Schema:
${schema}`;
}

const asStatus = (v) => (typeof v === 'string' && VALID_GATE_STATUS.has(v.toUpperCase()) ? v.toUpperCase() : null);
const asNumber = (v, min, max) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  if (n < min || n > max) return null;
  return n;
};

export function parseAndMapResearchJson(jsonText, currentFormData) {
  const parsed = JSON.parse(jsonText);
  const updates = { researchJson: JSON.stringify(parsed, null, 2) };
  const gateNotes = [];
  const scoreNotes = [];

  const edge = parsed?.qualitative_gates?.edge_proof;
  const gov = parsed?.qualitative_gates?.governance;

  const edgeStatus = asStatus(edge?.status);
  if (edgeStatus) updates.gateEdgeProof = edgeStatus;
  if (edge?.reason) gateNotes.push(`Edge-Proof: ${edge.reason}`);

  const govStatus = asStatus(gov?.status);
  if (govStatus) updates.gateGovernance = govStatus;
  if (gov?.reason) gateNotes.push(`Governance: ${gov.reason}`);

  const edgeOverride = parsed?.qualitative_scores?.edge_strength_override;
  const edgeValue = asNumber(edgeOverride?.value, 0, 30);
  if (edgeValue !== null) updates.scoreEdgeStrength = edgeValue;
  if (edgeOverride?.reason) scoreNotes.push(`Edge-Stärke Override: ${edgeOverride.reason}`);

  const summary = parsed?.summary || {};
  if (summary.thesis) updates.thesis = summary.thesis;
  if (summary.catalyst) updates.catalyst = summary.catalyst;
  if (summary.risks) updates.risk = summary.risks;

  const summaryParts = [summary.management_quality, summary.regulatory_context].filter(Boolean);
  if (summaryParts.length) {
    updates.summary = [currentFormData.summary, ...summaryParts].filter(Boolean).join('\n\n');
  }

  const overrides = parsed?.optional_overrides || {};
  const runwayStatus = asStatus(overrides.gateRunwayStatus);
  if (runwayStatus) updates.gateRunway = runwayStatus;
  const growthStatus = asStatus(overrides.gateGrowthConvexityStatus);
  if (growthStatus) updates.gateGrowthConvexity = growthStatus;

  const q = asNumber(overrides.scoreQuality, 0, 25);
  if (q !== null) updates.scoreQuality = q;
  const g = asNumber(overrides.scoreGrowthLeverage, 0, 25);
  if (g !== null) updates.scoreGrowthLeverage = g;
  const s = asNumber(overrides.scoreSatelliteFit, 0, 20);
  if (s !== null) updates.scoreSatelliteFit = s;

  if (gateNotes.length) updates.gateNotes = [currentFormData.gateNotes, ...gateNotes].filter(Boolean).join('\n');
  if (scoreNotes.length) updates.scoreNotes = [currentFormData.scoreNotes, ...scoreNotes].filter(Boolean).join('\n');

  return updates;
}
