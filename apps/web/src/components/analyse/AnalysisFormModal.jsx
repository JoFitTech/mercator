import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import pb from '@/lib/pocketbaseClient';
import { toast } from 'sonner';
import { Check, Copy, Database, FileJson } from 'lucide-react';
import {
  buildAutoDataNote,
  buildMetaBlock,
  buildResearchPrompt,
  deriveAutoGates,
  deriveAutoScores,
  normalizeBaseData,
  normalizeIdentifierInput,
  parseMetaBlock,
  parseResearchJson,
} from '@/lib/utils';

const ASSET_TYPES = ['Aktie', 'ETF', 'Pennystock'];
const ANALYSIS_TYPES = ['Satellite Checkliste', 'Breites Aktien-Framework', 'ETF-Framework'];
const GATE_STATUS = ['PASS', 'FAIL', 'OFFEN'];

const GATES = [
  { key: 'gateUniverseLiquidityStatus', label: 'Universum & Liquidität' },
  { key: 'gateRunwayStatus', label: 'Runway 18-24M' },
  { key: 'gateEdgeProofStatus', label: 'Edge-Proof' },
  { key: 'gateGrowthConvexityStatus', label: 'Wachstum/Konvexität' },
  { key: 'gateGovernanceStatus', label: 'Governance' },
  { key: 'gateTradingFeasibilityStatus', label: 'Trading-Feasibility' }
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
  analysisType: '',
  baseDataInput: '',
  researchInput: '',
  autoDataStatus: '',
  autoDataNote: '',
  baseDataJsonLocal: '',
  researchPromptLocal: '',
  researchJsonLocal: '',
  visibleGateNotes: '',
  visibleScoreNotes: ''
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

const deriveDecision = (data) => {
  const finalScore = ['scoreEdgeStrength', 'scoreQuality', 'scoreGrowthLeverage', 'scoreSatelliteFit'].reduce((sum, key) => sum + (Number(data[key]) || 0), 0);
  let decisionBucket = 'kein Kandidat';
  if (finalScore >= 90) decisionBucket = 'Booster';
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

const appendText = (base, lines = []) => [base, ...lines.filter(Boolean)].filter(Boolean).join('\n');

export default function AnalysisFormModal({ isOpen, onClose, analysis, onSuccess, initialTab = 'stammdaten' }) {
  const [formData, setFormData] = useState(DEFAULT_FORM_DATA);
  const [localUi, setLocalUi] = useState(DEFAULT_LOCAL_UI);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  const updateForm = (patch) => {
    setFormData((prev) => deriveDecision(typeof patch === 'function' ? patch(prev) : { ...prev, ...patch }));
  };

  useEffect(() => {
    if (!isOpen) return;

    const base = analysis ? { ...DEFAULT_FORM_DATA, ...analysis } : { ...DEFAULT_FORM_DATA };
    const gateParts = parseMetaBlock(base.gateNotes);
    const scoreParts = parseMetaBlock(base.scoreNotes);

    setFormData(deriveDecision({ ...base, gateNotes: base.gateNotes || '', scoreNotes: base.scoreNotes || '' }));
    setLocalUi({
      ...DEFAULT_LOCAL_UI,
      isin: gateParts.meta?.isin || '',
      wkn: gateParts.meta?.wkn || '',
      analysisType: gateParts.meta?.analysisType || '',
      autoDataStatus: gateParts.meta?.autoDataStatus || '',
      autoDataNote: gateParts.meta?.autoDataNote || '',
      baseDataJsonLocal: gateParts.meta?.baseDataJson || '',
      baseDataInput: gateParts.meta?.baseDataJson || '',
      researchPromptLocal: scoreParts.meta?.researchPrompt || '',
      researchJsonLocal: scoreParts.meta?.researchJson || '',
      researchInput: scoreParts.meta?.researchJson || '',
      visibleGateNotes: gateParts.visibleText || '',
      visibleScoreNotes: scoreParts.visibleText || ''
    });

    setErrors({});
    setActiveTab(initialTab);
  }, [isOpen, analysis, initialTab]);

  const handleChange = (field, value) => {
    updateForm({ [field]: value });
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: null }));
  };

  const handleLocalChange = (field, value) => {
    setLocalUi((prev) => ({ ...prev, [field]: value }));
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.ticker?.trim()) newErrors.ticker = 'Ticker ist erforderlich';
    if (!formData.companyName?.trim()) newErrors.companyName = 'Unternehmen ist erforderlich';
    if (!formData.assetType) newErrors.assetType = 'Asset-Typ ist erforderlich';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleAutoLookup = () => {
    const normalizedIds = normalizeIdentifierInput({ isin: localUi.isin, wkn: localUi.wkn, ticker: formData.ticker });
    if (!normalizedIds.lookup) {
      toast.error('Bitte ISIN, WKN oder Ticker angeben.');
      return;
    }

    setLocalUi((prev) => ({
      ...prev,
      isin: normalizedIds.isin,
      wkn: normalizedIds.wkn,
      autoDataStatus: 'Kein Live-Provider konfiguriert',
      autoDataNote: 'Bitte Basisdaten als JSON importieren. Der echte Identifier-Lookup ist in diesem Stand nicht aktiv.'
    }));

    updateForm({ ticker: normalizedIds.ticker || formData.ticker });
    setActiveTab('basisdaten');
    toast.info('Kein Live-Lookup aktiv. Bitte Basisdaten-JSON importieren.');
  };

  const handleBaseDataImport = () => {
    try {
      const parsed = JSON.parse(localUi.baseDataInput);
      const normalized = normalizeBaseData(parsed);
      const { gates } = deriveAutoGates(normalized);
      const { scores, notes } = deriveAutoScores(normalized);
      const autoNote = buildAutoDataNote({ normalizedData: normalized, gates, scores, notes });

      updateForm((prev) => ({
        ...prev,
        ticker: normalized.ticker || prev.ticker,
        companyName: normalized.companyName || prev.companyName,
        assetType: ['Aktie', 'ETF', 'Pennystock'].includes(normalized.assetType) ? normalized.assetType : prev.assetType,
        gateUniverseLiquidityStatus: gates.gateUniverseLiquidityStatus,
        gateRunwayStatus: gates.gateRunwayStatus,
        gateGrowthConvexityStatus: gates.gateGrowthConvexityStatus,
        gateTradingFeasibilityStatus: gates.gateTradingFeasibilityStatus,
        gateEdgeProofStatus: prev.gateEdgeProofStatus || 'OFFEN',
        gateGovernanceStatus: prev.gateGovernanceStatus || 'OFFEN',
        scoreQuality: scores.scoreQuality,
        scoreGrowthLeverage: scores.scoreGrowthLeverage,
        scoreSatelliteFit: scores.scoreSatelliteFit,
        scoreEdgeStrength: Number(prev.scoreEdgeStrength) || 0
      }));

      const gateSupplement = [
        'Automatische quantitative Vorbefüllung aus Basisdaten durchgeführt.',
        autoNote
      ].join('\n');

      const scoreSupplement = [
        `Qualitative Edge-Stärke bleibt unverändert (${formData.scoreEdgeStrength || 0}/30).`,
        ...notes
      ].join('\n');

      setLocalUi((prev) => ({
        ...prev,
        baseDataJsonLocal: JSON.stringify(parsed, null, 2),
        baseDataInput: JSON.stringify(parsed, null, 2),
        autoDataStatus: 'imported',
        autoDataNote: autoNote,
        visibleGateNotes: appendText(prev.visibleGateNotes, [gateSupplement]),
        visibleScoreNotes: appendText(prev.visibleScoreNotes, [scoreSupplement])
      }));

      setActiveTab('gates_scores');
      toast.success('Basisdaten importiert. Quantitative Gates/Scores wurden konservativ vorbefüllt.');
    } catch {
      toast.error('Basisdaten-JSON ist ungültig. Bitte ein valides JSON einfügen.');
    }
  };

  const handleGeneratePrompt = async () => {
    if (!formData.ticker?.trim() || !localUi.analysisType?.trim()) {
      toast.error('Für den Prompt sind mindestens Ticker und Analyse-Typ erforderlich.');
      return;
    }
    const prompt = buildResearchPrompt({ identifiers: { isin: localUi.isin, wkn: localUi.wkn, ticker: formData.ticker }, analysisType: localUi.analysisType, formData });
    setLocalUi((prev) => ({ ...prev, researchPromptLocal: prompt }));

    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedPrompt(true);
      setTimeout(() => setCopiedPrompt(false), 1500);
      toast.success('Research-Prompt generiert und kopiert.');
    } catch {
      toast.success('Research-Prompt generiert.');
    }
  };

  const handleResearchImport = () => {
    try {
      const { parsed, updates, gateNotes, scoreNotes } = parseResearchJson(localUi.researchInput);
      updateForm((prev) => ({ ...prev, ...updates }));
      setLocalUi((prev) => ({
        ...prev,
        researchJsonLocal: JSON.stringify(parsed, null, 2),
        researchInput: JSON.stringify(parsed, null, 2),
        visibleGateNotes: appendText(prev.visibleGateNotes, gateNotes),
        visibleScoreNotes: appendText(prev.visibleScoreNotes, scoreNotes)
      }));
      setActiveTab('qualitativ');
      toast.success('Research-JSON importiert und qualitative Felder übernommen.');
    } catch {
      toast.error('Research-JSON ist ungültig oder entspricht nicht dem erwarteten Schema.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) {
      toast.error('Bitte Pflichtfelder prüfen.');
      setActiveTab('stammdaten');
      return;
    }

    setIsSubmitting(true);
    try {
      const gateMeta = {
        isin: localUi.isin,
        wkn: localUi.wkn,
        analysisType: localUi.analysisType,
        autoDataStatus: localUi.autoDataStatus,
        autoDataNote: localUi.autoDataNote,
        baseDataJson: localUi.baseDataJsonLocal
      };

      const scoreMeta = {
        researchPrompt: localUi.researchPromptLocal,
        researchJson: localUi.researchJsonLocal
      };

      const payload = {
        ...formData,
        gateNotes: buildMetaBlock(localUi.visibleGateNotes, gateMeta),
        scoreNotes: buildMetaBlock(localUi.visibleScoreNotes, scoreMeta),
        userId: pb.authStore.model.id
      };

      const dataToSave = buildPersistedPayload(deriveDecision(payload));

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
      <DialogContent className="max-w-5xl max-h-[95vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="px-6 py-4 border-b bg-muted/10 shrink-0">
          <DialogTitle>{analysis ? 'Analyse bearbeiten' : 'Neue Analyse'}</DialogTitle>
          <p className="text-xs text-muted-foreground mt-1">
            1) Stammdaten eingeben · 2) Basisdaten JSON importieren · 3) quantitative Gates/Scores prüfen · 4) Research-Prompt generieren · 5) Research-JSON importieren · 6) final prüfen und speichern
          </p>
        </DialogHeader>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <div className="px-6 pt-2 border-b shrink-0">
            <TabsList className="w-full justify-start h-auto flex-wrap gap-2 bg-transparent p-0">
              <TabsTrigger value="stammdaten">Stammdaten</TabsTrigger>
              <TabsTrigger value="basisdaten">Basisdaten</TabsTrigger>
              <TabsTrigger value="gates_scores">Gates & Scores</TabsTrigger>
              <TabsTrigger value="qualitativ">Qualitativ</TabsTrigger>
              <TabsTrigger value="import">Import / AI</TabsTrigger>
            </TabsList>
          </div>
          <ScrollArea className="flex-1 p-6">
            <form id="analysis-form" onSubmit={handleSubmit} className="space-y-6">
              <TabsContent value="stammdaten" className="m-0 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2"><Label>Ticker *</Label><Input value={formData.ticker} onChange={(e) => handleChange('ticker', e.target.value.toUpperCase())} />{errors.ticker && <p className="text-xs text-destructive">{errors.ticker}</p>}</div>
                  <div className="space-y-2"><Label>Unternehmensname *</Label><Input value={formData.companyName} onChange={(e) => handleChange('companyName', e.target.value)} />{errors.companyName && <p className="text-xs text-destructive">{errors.companyName}</p>}</div>
                  <div className="space-y-2"><Label>Asset-Typ *</Label><Select value={formData.assetType} onValueChange={(v) => handleChange('assetType', v)}><SelectTrigger><SelectValue placeholder="Wählen" /></SelectTrigger><SelectContent>{ASSET_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent></Select>{errors.assetType && <p className="text-xs text-destructive">{errors.assetType}</p>}</div>
                  <div className="space-y-2"><Label>ISIN</Label><Input value={localUi.isin} onChange={(e) => handleLocalChange('isin', e.target.value.toUpperCase())} /></div>
                  <div className="space-y-2"><Label>WKN</Label><Input value={localUi.wkn} onChange={(e) => handleLocalChange('wkn', e.target.value.toUpperCase())} /></div>
                  <div className="space-y-2"><Label>Analyse-Typ</Label><Select value={localUi.analysisType} onValueChange={(v) => handleLocalChange('analysisType', v)}><SelectTrigger><SelectValue placeholder="Optional" /></SelectTrigger><SelectContent>{ANALYSIS_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent></Select></div>
                </div>
                <Button type="button" variant="outline" onClick={handleAutoLookup}><Database className="mr-2 h-4 w-4" />Identifier prüfen</Button>
              </TabsContent>

              <TabsContent value="basisdaten" className="m-0 space-y-4">
                <div className="p-4 rounded-lg border bg-muted/20 space-y-2">
                  <div className="flex items-center justify-between"><Label>AutoData-Status</Label><Badge variant="outline">{localUi.autoDataStatus || 'Noch keine Daten'}</Badge></div>
                  <p className="text-xs text-muted-foreground whitespace-pre-wrap">{localUi.autoDataNote || 'Kein echter Live-Provider konfiguriert. Für die quantitative Vorbefüllung bitte Basisdaten als JSON einfügen.'}</p>
                </div>
                <div className="p-4 rounded-lg border border-dashed space-y-3">
                  <p className="text-sm text-muted-foreground">Kein echter Live-Provider konfiguriert. Für die quantitative Vorbefüllung bitte Basisdaten als JSON einfügen.</p>
                  <Label>Basisdaten JSON</Label>
                  <Textarea className="font-mono text-xs min-h-[220px]" value={localUi.baseDataInput} onChange={(e) => handleLocalChange('baseDataInput', e.target.value)} placeholder='{"ticker":"AAPL","avgDollarVolume":12000000}' />
                  <Button type="button" onClick={handleBaseDataImport}><FileJson className="mr-2 h-4 w-4" />Basisdaten-JSON importieren</Button>
                </div>
              </TabsContent>

              <TabsContent value="gates_scores" className="m-0 space-y-6">
                <div className="grid md:grid-cols-2 gap-3">{GATES.map((g) => <div key={g.key} className="flex justify-between items-center border rounded p-3"><Label>{g.label}</Label><Select value={formData[g.key]} onValueChange={(v) => handleChange(g.key, v)}><SelectTrigger className="w-[120px]"><SelectValue /></SelectTrigger><SelectContent>{GATE_STATUS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select></div>)}</div>
                <div>
                  <Label>Gate Notes (sichtbar)</Label>
                  <Textarea value={localUi.visibleGateNotes} onChange={(e) => handleLocalChange('visibleGateNotes', e.target.value)} placeholder="Sichtbare Gate-Notizen" />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">{SCORES.map((s) => <div key={s.key} className="border rounded p-3"><Label>{s.label}</Label><Input type="number" min="0" max={s.max} value={formData[s.key]} onChange={(e) => handleChange(s.key, Math.min(s.max, Math.max(0, Number(e.target.value) || 0)))} /></div>)}</div>
                <div>
                  <Label>Score Notes (sichtbar)</Label>
                  <Textarea value={localUi.visibleScoreNotes} onChange={(e) => handleLocalChange('visibleScoreNotes', e.target.value)} placeholder="Sichtbare Score-Notizen" />
                </div>
              </TabsContent>

              <TabsContent value="qualitativ" className="m-0 grid md:grid-cols-2 gap-4">
                <Textarea value={formData.thesis} onChange={(e) => handleChange('thesis', e.target.value)} placeholder="These" className="min-h-[140px]" />
                <Textarea value={formData.summary} onChange={(e) => handleChange('summary', e.target.value)} placeholder="Summary" className="min-h-[140px]" />
                <Textarea value={formData.risk} onChange={(e) => handleChange('risk', e.target.value)} placeholder="Risiko" className="min-h-[140px]" />
                <Textarea value={formData.catalyst} onChange={(e) => handleChange('catalyst', e.target.value)} placeholder="Katalysator" className="min-h-[140px]" />
              </TabsContent>

              <TabsContent value="import" className="m-0 space-y-4">
                <div className="p-4 rounded-lg border space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Promptgenerator</Label>
                    <div className="flex gap-2">
                      <Button type="button" variant="outline" size="sm" disabled={!formData.ticker?.trim() || !localUi.analysisType?.trim()} onClick={handleGeneratePrompt}><FileJson className="h-4 w-4 mr-2" />Research-Prompt generieren</Button>
                      <Button type="button" variant="outline" size="sm" onClick={async () => {
                        if (!localUi.researchPromptLocal) return;
                        try {
                          await navigator.clipboard.writeText(localUi.researchPromptLocal);
                          setCopiedPrompt(true);
                          setTimeout(() => setCopiedPrompt(false), 1500);
                        } catch {
                          toast.error('Kopieren fehlgeschlagen.');
                        }
                      }}>{copiedPrompt ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}Copy</Button>
                    </div>
                  </div>
                  <Textarea className="font-mono text-xs min-h-[220px]" value={localUi.researchPromptLocal} onChange={(e) => handleLocalChange('researchPromptLocal', e.target.value)} placeholder="Prompt erscheint hier..." />
                </div>
                <div className="p-4 rounded-lg border border-dashed space-y-3">
                  <Label>Research JSON Import</Label>
                  <Textarea className="font-mono text-xs min-h-[220px]" value={localUi.researchInput} onChange={(e) => handleLocalChange('researchInput', e.target.value)} placeholder='{"qualitative_gates":{"edge_proof":{"status":"PASS"}}}' />
                  <Button type="button" onClick={handleResearchImport}><FileJson className="mr-2 h-4 w-4" />Research-JSON importieren</Button>
                </div>
              </TabsContent>
            </form>
          </ScrollArea>

          <DialogFooter className="px-6 py-4 border-t bg-muted/10 shrink-0">
            <div className="mr-auto text-sm text-muted-foreground">Score: <strong>{formData.finalScore}</strong> · Bucket: <strong>{formData.decisionBucket}</strong> · Entscheidung: <strong>{formData.finalDecision}</strong></div>
            <Button variant="outline" onClick={onClose}>Abbrechen</Button>
            <Button type="submit" form="analysis-form" disabled={isSubmitting}>{isSubmitting ? 'Speichere...' : analysis ? 'Aktualisieren' : 'Erstellen'}</Button>
          </DialogFooter>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
