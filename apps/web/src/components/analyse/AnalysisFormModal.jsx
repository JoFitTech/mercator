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
import { BrainCircuit, Check, Copy, Database, FileJson, Info } from 'lucide-react';
import {
  buildAutoDataNote,
  buildResearchPrompt,
  deriveAutoGates,
  deriveAutoScores,
  getResearchJsonSchema,
  mergeBaseDataIntoForm,
  normalizeBaseData,
  normalizeIdentifierInput,
  parseAndMapResearchJson
} from '@/lib/utils';

const ASSET_TYPES = ['Aktie', 'ETF', 'Pennystock'];
const ANALYSIS_TYPES = ['Satellite Checkliste', 'Breites Aktien-Framework', 'ETF-Framework'];
const GATE_STATUS = ['PASS', 'FAIL', 'OFFEN'];

const GATES = [
  { key: 'gateUniverseLiquidity', label: 'Universum & Liquidität' },
  { key: 'gateRunway', label: 'Runway 18-24M' },
  { key: 'gateEdgeProof', label: 'Edge-Proof' },
  { key: 'gateGrowthConvexity', label: 'Wachstum/Konvexität' },
  { key: 'gateGovernance', label: 'Governance' },
  { key: 'gateTradingFeasibility', label: 'Trading-Feasibility' }
];

const SCORES = [
  { key: 'scoreEdgeStrength', label: 'Edge-Stärke', max: 30 },
  { key: 'scoreQuality', label: 'Qualität', max: 25 },
  { key: 'scoreGrowthLeverage', label: 'Wachstum & Leverage', max: 25 },
  { key: 'scoreSatelliteFit', label: 'Satellite-Fit', max: 20 }
];

const DEFAULT_FORM_DATA = {
  ticker: '', companyName: '', assetType: '', isin: '', wkn: '', analysisType: '',
  exchange: '', country: '', region: '', sector: '', currency: '',
  price: '', marketCap: '', avgDollarVolume: '', spreadPct: '', earningsDate: '',
  daysToEarnings: '', ttmFcf: '', netCashFlag: false, runwayMonths: '',
  revenueCagr3y: '', marginTrend: '', dilutionTrend: '', volatilityBucket: '',
  terPct: '', domicile: '', replicationMethod: '', trackingDifferencePct: '',
  autoDataStatus: '', autoDataNote: '', baseDataJson: '',
  gateUniverseLiquidity: 'OFFEN', gateRunway: 'OFFEN', gateEdgeProof: 'OFFEN',
  gateGrowthConvexity: 'OFFEN', gateGovernance: 'OFFEN', gateTradingFeasibility: 'OFFEN', gateNotes: '',
  scoreEdgeStrength: 0, scoreQuality: 0, scoreGrowthLeverage: 0, scoreSatelliteFit: 0, scoreNotes: '',
  thesis: '', summary: '', risk: '', catalyst: '',
  researchPrompt: '', researchJson: '',
  finalScore: 0, decisionBucket: 'kein Kandidat', finalDecision: 'kein Kandidat'
};

const deriveDecision = (data) => {
  const finalScore = ['scoreEdgeStrength', 'scoreQuality', 'scoreGrowthLeverage', 'scoreSatelliteFit']
    .reduce((sum, key) => sum + (Number(data[key]) || 0), 0);

  let decisionBucket = 'kein Kandidat';
  if (finalScore >= 90) decisionBucket = 'Booster-Kandidat';
  else if (finalScore >= 85) decisionBucket = 'Kaufkandidat';
  else if (finalScore >= 75) decisionBucket = 'Watchlist';

  const hasFail = GATES.some((gate) => data[gate.key] === 'FAIL');
  const finalDecision = hasFail ? 'Ausschluss' : decisionBucket;

  return { ...data, finalScore, decisionBucket, finalDecision };
};

export default function AnalysisFormModal({ isOpen, onClose, analysis, onSuccess, initialTab = 'stammdaten' }) {
  const [formData, setFormData] = useState(DEFAULT_FORM_DATA);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [baseDataInput, setBaseDataInput] = useState('');
  const [researchInput, setResearchInput] = useState('');
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  const updateForm = (patch) => {
    setFormData((prev) => deriveDecision(typeof patch === 'function' ? patch(prev) : { ...prev, ...patch }));
  };

  useEffect(() => {
    if (!isOpen) return;
    const base = analysis ? { ...DEFAULT_FORM_DATA, ...analysis } : { ...DEFAULT_FORM_DATA };
    setFormData(deriveDecision(base));
    setBaseDataInput(analysis?.baseDataJson || '');
    setResearchInput(analysis?.researchJson || '');
    setErrors({});
    setActiveTab(initialTab);
  }, [isOpen, analysis, initialTab]);

  const handleChange = (field, value) => {
    updateForm({ [field]: value });
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: null }));
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
    const normalizedIds = normalizeIdentifierInput(formData);
    if (!normalizedIds.lookup) {
      toast.error('Bitte ISIN, WKN oder Ticker für den Lookup angeben.');
      return;
    }

    updateForm({
      isin: normalizedIds.isin,
      wkn: normalizedIds.wkn,
      ticker: normalizedIds.ticker,
      autoDataStatus: 'Kein Live-Provider konfiguriert',
      autoDataNote: 'Es ist aktuell kein echter Marktdaten-Provider eingebunden. Bitte Basisdaten als JSON einfügen. (Adapter-Stelle vorbereitet: handleAutoLookup -> providerAdapter.fetchByIdentifier)'
    });
    setActiveTab('basisdaten');
    toast.info('Kein Live-Lookup verfügbar. Bitte nutzen Sie den JSON-Fallback.');
  };

  const handleBaseDataImport = () => {
    try {
      const parsed = JSON.parse(baseDataInput);
      const normalized = normalizeBaseData(parsed);
      const { gates } = deriveAutoGates(normalized);
      const { scores } = deriveAutoScores(normalized);
      const autoNote = buildAutoDataNote({ normalizedData: normalized, gates, scores });
      const merged = mergeBaseDataIntoForm(formData, normalized, gates, scores, autoNote);
      updateForm(merged);
      setBaseDataInput(JSON.stringify(parsed, null, 2));
      toast.success('Basisdaten importiert und automatisch ausgewertet.');
      setActiveTab('basisdaten');
    } catch {
      toast.error('Ungültiges JSON für Basisdaten.');
    }
  };

  const handleGeneratePrompt = async () => {
    const prompt = buildResearchPrompt(formData);
    updateForm({ researchPrompt: prompt });
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
      const mapped = parseAndMapResearchJson(researchInput, formData);
      updateForm(mapped);
      toast.success('Research-JSON importiert und gemappt.');
      setActiveTab('qualitativ');
    } catch {
      toast.error('Ungültiges Research-JSON.');
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
      const dataToSave = { ...formData, userId: pb.authStore.model.id };
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
                  <div className="space-y-2"><Label>Ticker *</Label><Input value={formData.ticker} onChange={(e) => handleChange('ticker', e.target.value.toUpperCase())} /></div>
                  <div className="space-y-2"><Label>Unternehmen *</Label><Input value={formData.companyName} onChange={(e) => handleChange('companyName', e.target.value)} /></div>
                  <div className="space-y-2"><Label>Asset-Typ *</Label><Select value={formData.assetType} onValueChange={(v) => handleChange('assetType', v)}><SelectTrigger><SelectValue placeholder="Wählen" /></SelectTrigger><SelectContent>{ASSET_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent></Select></div>
                  <div className="space-y-2"><Label>ISIN</Label><Input value={formData.isin} onChange={(e) => handleChange('isin', e.target.value.toUpperCase())} /></div>
                  <div className="space-y-2"><Label>WKN</Label><Input value={formData.wkn} onChange={(e) => handleChange('wkn', e.target.value.toUpperCase())} /></div>
                  <div className="space-y-2"><Label>Analyse-Typ</Label><Select value={formData.analysisType} onValueChange={(v) => handleChange('analysisType', v)}><SelectTrigger><SelectValue placeholder="Optional" /></SelectTrigger><SelectContent>{ANALYSIS_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent></Select></div>
                </div>
                <Button type="button" variant="outline" onClick={handleAutoLookup}><Database className="mr-2 h-4 w-4" />Identifier prüfen & Auto-Lookup starten</Button>
              </TabsContent>

              <TabsContent value="basisdaten" className="m-0 space-y-4">
                <div className="p-4 rounded-lg border bg-muted/20 space-y-2">
                  <div className="flex items-center justify-between"><Label>Auto-Fill Status</Label><Badge variant="outline">{formData.autoDataStatus || 'Noch keine Daten'}</Badge></div>
                  <p className="text-xs text-muted-foreground whitespace-pre-wrap">{formData.autoDataNote || 'Noch keine automatische Vorbefüllung vorhanden.'}</p>
                </div>
                <div className="p-4 rounded-lg border border-dashed space-y-3">
                  <Label>Basisdaten JSON Fallback</Label>
                  <Textarea className="font-mono text-xs min-h-[220px]" value={baseDataInput} onChange={(e) => setBaseDataInput(e.target.value)} placeholder='{"ticker":"AAPL","marketCap":3000000000000}' />
                  <Button type="button" onClick={handleBaseDataImport}><FileJson className="mr-2 h-4 w-4" />Basisdaten-JSON importieren</Button>
                </div>
              </TabsContent>

              <TabsContent value="gates_scores" className="m-0 space-y-6">
                <div className="grid md:grid-cols-2 gap-3">{GATES.map((g) => <div key={g.key} className="flex justify-between items-center border rounded p-3"><Label>{g.label}</Label><Select value={formData[g.key]} onValueChange={(v) => handleChange(g.key, v)}><SelectTrigger className="w-[120px]"><SelectValue /></SelectTrigger><SelectContent>{GATE_STATUS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select></div>)}</div>
                <Textarea value={formData.gateNotes} onChange={(e) => handleChange('gateNotes', e.target.value)} placeholder="Gate Notes" />
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">{SCORES.map((s) => <div key={s.key} className="border rounded p-3"><Label>{s.label}</Label><Input type="number" min="0" max={s.max} value={formData[s.key]} onChange={(e) => handleChange(s.key, Math.min(s.max, Math.max(0, Number(e.target.value) || 0)))} /></div>)}</div>
                <Textarea value={formData.scoreNotes} onChange={(e) => handleChange('scoreNotes', e.target.value)} placeholder="Score Notes" />
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
                    <Button type="button" variant="outline" size="sm" onClick={handleGeneratePrompt}>{copiedPrompt ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}Research-Prompt generieren</Button>
                  </div>
                  <Textarea value={formData.researchPrompt} onChange={(e) => handleChange('researchPrompt', e.target.value)} className="font-mono text-xs min-h-[160px]" placeholder="Prompt wird hier erzeugt..." />
                </div>
                <div className="p-4 rounded-lg border bg-muted/10 space-y-2">
                  <div className="flex items-center gap-2 text-sm"><Info className="h-4 w-4" /> JSON-Schema</div>
                  <pre className="text-xs overflow-auto max-h-[220px] bg-background p-2 rounded border">{JSON.stringify(getResearchJsonSchema(), null, 2)}</pre>
                </div>
                <div className="p-4 rounded-lg border space-y-3">
                  <Label>Research-JSON Import</Label>
                  <Textarea value={researchInput} onChange={(e) => setResearchInput(e.target.value)} className="font-mono text-xs min-h-[180px]" placeholder='{"qualitative_gates":{...}}' />
                  <Button type="button" onClick={handleResearchImport}><BrainCircuit className="h-4 w-4 mr-2" />Research-JSON importieren</Button>
                </div>
              </TabsContent>
            </form>
          </ScrollArea>
          <DialogFooter className="px-4 py-3 border-t flex items-center justify-between">
            <div className="flex items-center gap-3 text-sm">
              <Badge variant="outline">Score: {formData.finalScore}</Badge>
              <Badge variant="outline">Bucket: {formData.decisionBucket}</Badge>
              <Badge variant={formData.finalDecision === 'Ausschluss' ? 'destructive' : 'secondary'}>{formData.finalDecision}</Badge>
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={onClose}>Abbrechen</Button>
              <Button type="submit" form="analysis-form" disabled={isSubmitting}>{isSubmitting ? 'Speichern...' : 'Analyse speichern'}</Button>
            </div>
          </DialogFooter>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
