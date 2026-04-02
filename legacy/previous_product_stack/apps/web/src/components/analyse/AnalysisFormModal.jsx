import React, { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import pb from '@/lib/pocketbaseClient';
import { toast } from 'sonner';
import { Check, Copy, FileJson } from 'lucide-react';
import { buildResearchPrompt, getResearchJsonSchema, mergeVisibleTextWithMeta, parseMetaBlock } from '@/lib/utils';

const ASSET_TYPES = ['Aktie', 'ETF', 'Pennystock'];
const ANALYSIS_TYPES = ['Satellite Checkliste', 'Breites Aktien-Framework', 'ETF-Framework'];
const FORMAT_OPTIONS = ['JSON', 'YAML', 'XML'];
const GATE_STATUS = ['PASS', 'FAIL', 'OFFEN'];

const GATES = [
  {
    key: 'gateUniverseLiquidityStatus',
    label: 'Universum & Liquidität',
    help: 'Börse, Market Cap, Handelsvolumen und Spread müssen für eine handelbare Satellitenposition ausreichen.'
  },
  {
    key: 'gateRunwayStatus',
    label: 'Runway 18-24M',
    help: 'Pass wenn Net Cash oder positiver TTM FCF oder Runway >= 18 Monate. Fail bei absehbarer Refinanzierung ohne Plan.'
  },
  {
    key: 'gateEdgeProofStatus',
    label: 'Edge-Proof',
    help: 'Mindestens zwei belastbare Proxies wie Bottleneck, Switching Costs, Regulatorik oder Netzwerk.'
  },
  {
    key: 'gateGrowthConvexityStatus',
    label: 'Wachstum/Konvexität',
    help: 'Gutes Wachstum mit stabilem oder verbessertem Margen-/FCF-Pfad.'
  },
  {
    key: 'gateGovernanceStatus',
    label: 'Governance',
    help: 'Keine schweren Red Flags wie Restatement, Material Weakness, Going Concern oder ungeklärte schwere Vorwürfe.'
  },
  {
    key: 'gateTradingFeasibilityStatus',
    label: 'Trading-Feasibility',
    help: 'Position muss unter Risikoregeln handelbar sein; Earnings-Nähe und Ausführung beachten.'
  }
];

const SCORES = [
  { key: 'scoreEdgeStrength', label: 'Edge-Stärke', max: 30 },
  { key: 'scoreQuality', label: 'Qualität', max: 25 },
  { key: 'scoreGrowthLeverage', label: 'Wachstum & Leverage', max: 25 },
  { key: 'scoreSatelliteFit', label: 'Satellite-Fit', max: 20 }
];

const DEFAULT_FORM_DATA = {
  ticker: '',
  companyName: '',
  assetType: '',
  thesis: '',
  summary: '',
  risk: '',
  catalyst: '',
  gateUniverseLiquidityStatus: 'OFFEN',
  gateRunwayStatus: 'OFFEN',
  gateEdgeProofStatus: 'OFFEN',
  gateGrowthConvexityStatus: 'OFFEN',
  gateGovernanceStatus: 'OFFEN',
  gateTradingFeasibilityStatus: 'OFFEN',
  gateNotes: '',
  scoreEdgeStrength: 0,
  scoreQuality: 0,
  scoreGrowthLeverage: 0,
  scoreSatelliteFit: 0,
  scoreNotes: '',
  finalScore: 0,
  decisionBucket: 'kein Kandidat',
  finalDecision: 'kein Kandidat'
};

const DEFAULT_LOCAL_UI = {
  isin: '',
  wkn: '',
  analysisType: 'Satellite Checkliste',
  importFormatPreference: 'JSON',
  importSourceHint: 'Manueller Research-Import',
  generatedPrompt: '',
  researchInput: '',
  importedRawPayload: '',
  importedPayloadFormat: 'JSON',
  lastImportAt: '',
  visibleGateNotes: '',
  visibleScoreNotes: '',
  importStatus: ''
};

const PERSISTED_FIELDS = [
  'ticker',
  'companyName',
  'assetType',
  'thesis',
  'summary',
  'risk',
  'catalyst',
  'gateUniverseLiquidityStatus',
  'gateRunwayStatus',
  'gateEdgeProofStatus',
  'gateGrowthConvexityStatus',
  'gateGovernanceStatus',
  'gateTradingFeasibilityStatus',
  'gateNotes',
  'scoreEdgeStrength',
  'scoreQuality',
  'scoreGrowthLeverage',
  'scoreSatelliteFit',
  'scoreNotes',
  'finalScore',
  'decisionBucket',
  'finalDecision',
  'userId'
];

const clampScore = (value, max) => Math.min(max, Math.max(0, Number(value) || 0));
const sanitizeStatus = (status) => (GATE_STATUS.includes((status || '').toUpperCase()) ? (status || '').toUpperCase() : null);
const pushNote = (base, lines = []) => [base, ...lines.filter(Boolean)].filter(Boolean).join('\n\n').trim();

const deriveDecision = (data) => {
  const finalScore = ['scoreEdgeStrength', 'scoreQuality', 'scoreGrowthLeverage', 'scoreSatelliteFit'].reduce((sum, key) => sum + (Number(data[key]) || 0), 0);
  let decisionBucket = 'kein Kandidat';
  if (finalScore >= 90) decisionBucket = 'Booster-Kandidat';
  else if (finalScore >= 85) decisionBucket = 'Kaufkandidat';
  else if (finalScore >= 75) decisionBucket = 'Watchlist';

  const hasFail = GATES.some((gate) => data[gate.key] === 'FAIL');
  const finalDecision = hasFail ? 'Ausschluss' : decisionBucket;
  return { ...data, finalScore, decisionBucket, finalDecision };
};

const buildPersistedPayload = (formData) => PERSISTED_FIELDS.reduce((acc, key) => {
  if (formData[key] !== undefined) acc[key] = formData[key];
  return acc;
}, {});

const parseAndMapResearch = (rawInput) => {
  const trimmed = (rawInput || '').trim();
  if (!trimmed) throw new Error('Bitte JSON für den Import einfügen.');

  let parsed;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    throw new Error('Ungültiges JSON. Bitte valide JSON-Daten einfügen.');
  }

  const updates = {};
  const gateNotes = [];
  const scoreNotes = [];

  const gateMappings = [
    ['universe_liquidity', 'gateUniverseLiquidityStatus', 'Universum & Liquidität'],
    ['runway_18_24m', 'gateRunwayStatus', 'Runway 18-24M'],
    ['edge_proof', 'gateEdgeProofStatus', 'Edge-Proof'],
    ['growth_convexity', 'gateGrowthConvexityStatus', 'Wachstum/Konvexität'],
    ['governance', 'gateGovernanceStatus', 'Governance'],
    ['trading_feasibility', 'gateTradingFeasibilityStatus', 'Trading-Feasibility']
  ];

  const invalidStatuses = [];
  gateMappings.forEach(([sourceKey, targetKey, label]) => {
    const node = parsed?.gates?.[sourceKey];
    if (!node) return;

    const status = sanitizeStatus(node.status);
    if (node.status !== undefined && !status) invalidStatuses.push(`${label}: ${node.status}`);
    if (status) updates[targetKey] = status;

    if (node.reason) gateNotes.push(`${label}: ${String(node.reason)}`);
    if (Array.isArray(node.evidence) && node.evidence.length) {
      gateNotes.push(`${label} Evidenz: ${node.evidence.join(' | ')}`);
    }
  });

  if (invalidStatuses.length) {
    throw new Error(`Ungültige Gate-Status gefunden (${invalidStatuses.join(', ')}). Erlaubt sind PASS, FAIL oder OFFEN.`);
  }

  const scoreMappings = [
    ['edge_strength', 'scoreEdgeStrength', 30, 'Edge-Stärke'],
    ['quality', 'scoreQuality', 25, 'Qualität'],
    ['growth_leverage', 'scoreGrowthLeverage', 25, 'Wachstum & Leverage'],
    ['satellite_fit', 'scoreSatelliteFit', 20, 'Satellite-Fit']
  ];

  const invalidScores = [];
  scoreMappings.forEach(([sourceKey, targetKey, max, label]) => {
    const node = parsed?.scores?.[sourceKey];
    if (!node || node.value === undefined || node.value === null || node.value === '') return;

    const numeric = Number(node.value);
    if (!Number.isFinite(numeric)) {
      invalidScores.push(`${label}: ${node.value}`);
      return;
    }

    if (numeric < 0 || numeric > max) {
      updates[targetKey] = clampScore(numeric, max);
      invalidScores.push(`${label}: ${node.value} (auf 0-${max} begrenzt)`);
    } else {
      updates[targetKey] = numeric;
    }

    if (node.reason) scoreNotes.push(`${label}: ${String(node.reason)}`);
  });

  if (invalidScores.some((item) => !item.includes('begrenzt'))) {
    throw new Error(`Ungültige Score-Werte gefunden (${invalidScores.join(', ')}).`);
  }

  if (parsed?.summary?.thesis) updates.thesis = String(parsed.summary.thesis);
  if (parsed?.summary?.summary) updates.summary = String(parsed.summary.summary);
  if (parsed?.summary?.catalyst) updates.catalyst = String(parsed.summary.catalyst);
  if (parsed?.summary?.risks) updates.risk = String(parsed.summary.risks);

  if (parsed?.summary?.management_quality) gateNotes.push(`Management-Qualität: ${String(parsed.summary.management_quality)}`);
  if (parsed?.summary?.regulatory_context) gateNotes.push(`Regulatorik-Kontext: ${String(parsed.summary.regulatory_context)}`);

  return { parsed, updates, gateNotes, scoreNotes, warnings: invalidScores.filter((item) => item.includes('begrenzt')) };
};

export default function AnalysisFormModal({ isOpen, onClose, analysis, onSuccess, initialTab = 'stammdaten' }) {
  const [formData, setFormData] = useState(DEFAULT_FORM_DATA);
  const [localUi, setLocalUi] = useState(DEFAULT_LOCAL_UI);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  const schemaPreview = useMemo(() => JSON.stringify(getResearchJsonSchema(), null, 2), []);

  const updateForm = (patch) => {
    setFormData((prev) => deriveDecision(typeof patch === 'function' ? patch(prev) : { ...prev, ...patch }));
  };

  useEffect(() => {
    if (!isOpen) return;

    const base = analysis ? { ...DEFAULT_FORM_DATA, ...analysis } : { ...DEFAULT_FORM_DATA };
    const gateParts = parseMetaBlock(base.gateNotes || '');
    const scoreParts = parseMetaBlock(base.scoreNotes || '');

    setFormData(deriveDecision({ ...base }));
    setLocalUi({
      ...DEFAULT_LOCAL_UI,
      isin: gateParts.meta?.isin || '',
      wkn: gateParts.meta?.wkn || '',
      analysisType: gateParts.meta?.analysisType || 'Satellite Checkliste',
      importFormatPreference: gateParts.meta?.importFormatPreference || 'JSON',
      importSourceHint: gateParts.meta?.importSourceHint || 'Manueller Research-Import',
      generatedPrompt: scoreParts.meta?.generatedPrompt || '',
      researchInput: scoreParts.meta?.importedRawPayload || '',
      importedRawPayload: scoreParts.meta?.importedRawPayload || '',
      importedPayloadFormat: scoreParts.meta?.importedPayloadFormat || 'JSON',
      lastImportAt: scoreParts.meta?.lastImportAt || '',
      visibleGateNotes: gateParts.visibleText || '',
      visibleScoreNotes: scoreParts.visibleText || '',
      importStatus: ''
    });

    setErrors({});
    setActiveTab(initialTab);
  }, [isOpen, analysis, initialTab]);

  const handleChange = (field, value) => {
    updateForm({ [field]: value });
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: null }));
  };

  const handleLocalChange = (field, value) => setLocalUi((prev) => ({ ...prev, [field]: value }));

  const validate = () => {
    const nextErrors = {};
    if (!formData.ticker?.trim()) nextErrors.ticker = 'Ticker ist erforderlich.';
    if (!formData.companyName?.trim()) nextErrors.companyName = 'Unternehmensname ist erforderlich.';
    if (!formData.assetType) nextErrors.assetType = 'Asset-Typ ist erforderlich.';
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleGeneratePrompt = () => {
    if (!formData.ticker?.trim()) {
      toast.error('Ticker ist erforderlich.');
      setActiveTab('stammdaten');
      return;
    }
    if (!formData.companyName?.trim()) {
      toast.error('Unternehmensname ist erforderlich.');
      setActiveTab('stammdaten');
      return;
    }
    if (!formData.assetType) {
      toast.error('Asset-Typ ist erforderlich.');
      setActiveTab('stammdaten');
      return;
    }

    const prompt = buildResearchPrompt({
      identifiers: { isin: localUi.isin, wkn: localUi.wkn, ticker: formData.ticker },
      analysisType: localUi.analysisType || 'Satellite Checkliste',
      formData,
      formatPreference: localUi.importFormatPreference || 'JSON'
    });

    setLocalUi((prev) => ({ ...prev, generatedPrompt: prompt }));
    toast.success('Research-Prompt wurde generiert.');
  };

  const handleCopyPrompt = async () => {
    if (!localUi.generatedPrompt) return;
    try {
      await navigator.clipboard.writeText(localUi.generatedPrompt);
      setCopiedPrompt(true);
      setTimeout(() => setCopiedPrompt(false), 1500);
      toast.success('Prompt kopiert.');
    } catch {
      toast.error('Kopieren fehlgeschlagen.');
    }
  };

  const handleResearchImport = () => {
    try {
      const { parsed, updates, gateNotes, scoreNotes, warnings } = parseAndMapResearch(localUi.researchInput);
      updateForm((prev) => ({ ...prev, ...updates }));

      const serialized = JSON.stringify(parsed, null, 2);
      const now = new Date().toISOString();
      setLocalUi((prev) => ({
        ...prev,
        researchInput: serialized,
        importedRawPayload: serialized.slice(0, 20000),
        importedPayloadFormat: 'JSON',
        lastImportAt: now,
        importStatus: warnings.length
          ? `Import erfolgreich mit Begrenzung: ${warnings.join('; ')}`
          : 'Import erfolgreich. Gates, Scores und Freitexte wurden übernommen.',
        visibleGateNotes: pushNote(prev.visibleGateNotes, gateNotes),
        visibleScoreNotes: pushNote(prev.visibleScoreNotes, scoreNotes)
      }));

      if (warnings.length) toast.warning('Import erfolgreich mit Score-Begrenzung. Details im Statusfeld.');
      else toast.success('JSON-Import erfolgreich.');
    } catch (error) {
      const message = error?.message || 'Import fehlgeschlagen.';
      setLocalUi((prev) => ({ ...prev, importStatus: message }));
      toast.error(message);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) {
      toast.error('Bitte Pflichtfelder ausfüllen.');
      setActiveTab('stammdaten');
      return;
    }

    setIsSubmitting(true);
    try {
      const gateMeta = {
        isin: localUi.isin || '',
        wkn: localUi.wkn || '',
        analysisType: localUi.analysisType || 'Satellite Checkliste',
        importFormatPreference: localUi.importFormatPreference || 'JSON',
        importSourceHint: localUi.importSourceHint || 'Manueller Research-Import'
      };

      const scoreMeta = {
        generatedPrompt: localUi.generatedPrompt || '',
        importedRawPayload: (localUi.importedRawPayload || '').slice(0, 20000),
        importedPayloadFormat: localUi.importedPayloadFormat || 'JSON',
        lastImportAt: localUi.lastImportAt || ''
      };

      const payload = deriveDecision({
        ...formData,
        gateNotes: mergeVisibleTextWithMeta(localUi.visibleGateNotes, gateMeta),
        scoreNotes: mergeVisibleTextWithMeta(localUi.visibleScoreNotes, scoreMeta),
        userId: pb.authStore.model?.id
      });

      const dataToSave = buildPersistedPayload(payload);

      if (analysis?.id) {
        await pb.collection('analyses').update(analysis.id, dataToSave, { $autoCancel: false });
        toast.success('Analyse aktualisiert.');
      } else {
        await pb.collection('analyses').create(dataToSave, { $autoCancel: false });
        toast.success('Analyse erstellt.');
      }

      onSuccess();
      onClose();
    } catch (error) {
      toast.error(error.response?.message || 'Fehler beim Speichern.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl w-[96vw] h-[92vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="px-4 md:px-6 py-4 border-b bg-background shrink-0 sticky top-0 z-20">
          <DialogTitle>{analysis ? 'Analyse bearbeiten' : 'Neue Analyse'}</DialogTitle>
          <p className="text-xs text-muted-foreground mt-1">Robuster manueller Workflow: Prompt generieren, extern recherchieren, JSON importieren, prüfen und speichern.</p>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 min-h-0 flex flex-col">
          <div className="px-4 md:px-6 py-2 border-b bg-background sticky top-0 z-10 shrink-0">
            <TabsList className="w-full h-auto flex-wrap justify-start gap-2 bg-transparent p-0">
              <TabsTrigger value="stammdaten">Stammdaten</TabsTrigger>
              <TabsTrigger value="gates_scores">Gates & Scores</TabsTrigger>
              <TabsTrigger value="qualitativ">Qualitativ</TabsTrigger>
              <TabsTrigger value="import">Import / AI</TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4">
            <form id="analysis-form" onSubmit={handleSubmit} className="space-y-6 pb-6">
              <TabsContent value="stammdaten" className="m-0 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Ticker *</Label>
                    <Input value={formData.ticker} onChange={(e) => handleChange('ticker', e.target.value.toUpperCase())} />
                    {errors.ticker && <p className="text-xs text-destructive">{errors.ticker}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label>Unternehmensname *</Label>
                    <Input value={formData.companyName} onChange={(e) => handleChange('companyName', e.target.value)} />
                    {errors.companyName && <p className="text-xs text-destructive">{errors.companyName}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label>Asset-Typ *</Label>
                    <Select value={formData.assetType} onValueChange={(v) => handleChange('assetType', v)}>
                      <SelectTrigger><SelectValue placeholder="Wählen" /></SelectTrigger>
                      <SelectContent>{ASSET_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                    </Select>
                    {errors.assetType && <p className="text-xs text-destructive">{errors.assetType}</p>}
                  </div>
                  <div className="space-y-2"><Label>ISIN (optional)</Label><Input value={localUi.isin} onChange={(e) => handleLocalChange('isin', e.target.value.toUpperCase())} /></div>
                  <div className="space-y-2"><Label>WKN (optional)</Label><Input value={localUi.wkn} onChange={(e) => handleLocalChange('wkn', e.target.value.toUpperCase())} /></div>
                  <div className="space-y-2">
                    <Label>Analyse-Typ (optional)</Label>
                    <Select value={localUi.analysisType} onValueChange={(v) => handleLocalChange('analysisType', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>{ANALYSIS_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2 md:col-span-2 lg:col-span-1">
                    <Label>Gewünschtes Rückgabeformat</Label>
                    <Select value={localUi.importFormatPreference} onValueChange={(v) => handleLocalChange('importFormatPreference', v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>{FORMAT_OPTIONS.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">Import unterstützt in dieser Version zuverlässig nur JSON.</p>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="gates_scores" className="m-0 space-y-6">
                <div className="grid md:grid-cols-2 gap-4">
                  {GATES.map((gate) => (
                    <div key={gate.key} className="border rounded-md p-3 space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <Label>{gate.label}</Label>
                        <Select value={formData[gate.key]} onValueChange={(v) => handleChange(gate.key, v)}>
                          <SelectTrigger className="w-[120px]"><SelectValue /></SelectTrigger>
                          <SelectContent>{GATE_STATUS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                      <p className="text-xs text-muted-foreground">{gate.help}</p>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {SCORES.map((score) => (
                    <div key={score.key} className="border rounded-md p-3 space-y-1">
                      <Label>{score.label}</Label>
                      <p className="text-xs text-muted-foreground">Max. {score.max} Punkte</p>
                      <Input type="number" min="0" max={score.max} value={formData[score.key]} onChange={(e) => handleChange(score.key, clampScore(e.target.value, score.max))} />
                    </div>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="qualitativ" className="m-0 space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>These</Label><Textarea className="min-h-[140px]" value={formData.thesis} onChange={(e) => handleChange('thesis', e.target.value)} /></div>
                  <div className="space-y-2"><Label>Summary</Label><Textarea className="min-h-[140px]" value={formData.summary} onChange={(e) => handleChange('summary', e.target.value)} /></div>
                  <div className="space-y-2"><Label>Risiko</Label><Textarea className="min-h-[140px]" value={formData.risk} onChange={(e) => handleChange('risk', e.target.value)} /></div>
                  <div className="space-y-2"><Label>Katalysator</Label><Textarea className="min-h-[140px]" value={formData.catalyst} onChange={(e) => handleChange('catalyst', e.target.value)} /></div>
                </div>
                <div className="space-y-2"><Label>Sichtbare Gate-Notizen</Label><Textarea className="min-h-[140px]" value={localUi.visibleGateNotes} onChange={(e) => handleLocalChange('visibleGateNotes', e.target.value)} /></div>
                <div className="space-y-2"><Label>Sichtbare Score-Notizen</Label><Textarea className="min-h-[140px]" value={localUi.visibleScoreNotes} onChange={(e) => handleLocalChange('visibleScoreNotes', e.target.value)} /></div>
              </TabsContent>

              <TabsContent value="import" className="m-0 space-y-4">
                <div className="border rounded-md p-4 text-sm text-muted-foreground">
                  Diese Analyse arbeitet in dieser Version rein manuell. Die App erzeugt einen Research-Prompt; das externe Ergebnis wird anschließend als JSON importiert. Kein Live-Lookup und kein Auto-Import aktiv.
                </div>

                <div className="border rounded-md p-4 space-y-3">
                  <div className="flex flex-wrap gap-2 justify-between items-center">
                    <h3 className="font-medium">Promptgenerator</h3>
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" variant="outline" onClick={handleGeneratePrompt}><FileJson className="h-4 w-4 mr-2" />Research-Prompt generieren</Button>
                      <Button type="button" variant="outline" onClick={handleCopyPrompt} disabled={!localUi.generatedPrompt}>{copiedPrompt ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}Copy</Button>
                    </div>
                  </div>
                  <Textarea readOnly className="font-mono text-xs min-h-[260px]" value={localUi.generatedPrompt} placeholder="Der generierte Research-Prompt erscheint hier..." />
                </div>

                <div className="border rounded-md p-4 space-y-3">
                  <h3 className="font-medium">JSON-Import</h3>
                  <Textarea className="font-mono text-xs min-h-[240px]" value={localUi.researchInput} onChange={(e) => handleLocalChange('researchInput', e.target.value)} placeholder='{"asset":{},"gates":{},"scores":{},"summary":{},"result":{}}' />
                  <Button type="button" onClick={handleResearchImport}><FileJson className="h-4 w-4 mr-2" />JSON importieren</Button>
                  {localUi.importStatus && <p className="text-sm text-muted-foreground whitespace-pre-wrap">{localUi.importStatus}</p>}
                </div>

                <div className="border rounded-md p-4 space-y-2">
                  <h3 className="font-medium">JSON-Schema-Vorschau</h3>
                  <Textarea readOnly className="font-mono text-xs min-h-[260px]" value={schemaPreview} />
                </div>
              </TabsContent>
            </form>
          </div>

          <DialogFooter className="px-4 md:px-6 py-4 border-t bg-background shrink-0 sticky bottom-0 z-20">
            <div className="mr-auto text-xs md:text-sm text-muted-foreground">Score: <strong>{formData.finalScore}</strong> · Bucket: <strong>{formData.decisionBucket}</strong> · Entscheidung: <strong>{formData.finalDecision}</strong></div>
            <Button variant="outline" onClick={onClose}>Abbrechen</Button>
            <Button type="submit" form="analysis-form" disabled={isSubmitting}>{isSubmitting ? 'Speichere...' : analysis ? 'Aktualisieren' : 'Speichern'}</Button>
          </DialogFooter>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
