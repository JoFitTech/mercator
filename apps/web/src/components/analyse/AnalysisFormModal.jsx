
import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
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
import { AlertTriangle, Database, BrainCircuit, FileJson, Copy, Check } from 'lucide-react';

const ASSET_TYPES = ['Aktie', 'ETF', 'Pennystock'];
const ANALYSIS_TYPES = ['Satellite Checkliste', 'Breites Aktien-Framework', 'ETF-Framework'];
const GATE_STATUS = ['PASS', 'FAIL', 'OFFEN'];
const TRENDS = ['stabil', 'verbessernd', 'verschlechternd'];
const DILUTION_TRENDS = ['niedrig', 'stabil', 'erhöht'];

const GATES = [
  { key: 'gateUniverseLiquidity', label: 'Universum & Liquidität', help: 'Börse, Market Cap, Volumen, Spread ausreichend' },
  { key: 'gateRunway', label: 'Runway 18-24M', help: 'Net Cash oder TTM FCF > 0 oder ausreichender Runway' },
  { key: 'gateEdgeProof', label: 'Edge-Proof', help: 'Mindestens 2 Proxies wie Bottleneck, Switching, Regulatorik oder Netzwerk' },
  { key: 'gateGrowthConvexity', label: 'Wachstum/Konvexität', help: 'Gutes Wachstum und stabile oder verbesserte Margen' },
  { key: 'gateGovernance', label: 'Governance', help: 'Keine schweren Red Flags' },
  { key: 'gateTradingFeasibility', label: 'Trading-Feasibility', help: 'Ausführung und Risiko praktikabel' }
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
  scoreEdgeStrength: 0, scoreQuality: 0, scoreGrowthLeverage: 0, scoreSatelliteFit: 0,
  thesis: '', summary: '', risk: '', catalyst: '',
  researchPrompt: '', researchJson: '',
  finalScore: 0, decisionBucket: 'kein Kandidat', finalDecision: 'kein Kandidat'
};

export default function AnalysisFormModal({ isOpen, onClose, analysis, onSuccess, initialTab = 'stammdaten' }) {
  const [formData, setFormData] = useState(DEFAULT_FORM_DATA);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab);
  
  // Import states
  const [baseDataInput, setBaseDataInput] = useState('');
  const [researchInput, setResearchInput] = useState('');
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (analysis) {
        setFormData({ ...DEFAULT_FORM_DATA, ...analysis });
        setBaseDataInput(analysis.baseDataJson || '');
        setResearchInput(analysis.researchJson || '');
      } else {
        setFormData(DEFAULT_FORM_DATA);
        setBaseDataInput('');
        setResearchInput('');
      }
      setErrors({});
      setActiveTab(initialTab);
    }
  }, [isOpen, analysis, initialTab]);

  // Auto-calculate scores and decisions
  useEffect(() => {
    const totalScore = 
      (Number(formData.scoreEdgeStrength) || 0) +
      (Number(formData.scoreQuality) || 0) +
      (Number(formData.scoreGrowthLeverage) || 0) +
      (Number(formData.scoreSatelliteFit) || 0);

    let bucket = 'kein Kandidat';
    if (totalScore >= 90) bucket = 'Booster-Kandidat';
    else if (totalScore >= 85) bucket = 'Kaufkandidat';
    else if (totalScore >= 75) bucket = 'Watchlist';

    const hasFail = GATES.some(gate => formData[gate.key] === 'FAIL');
    const decision = hasFail ? 'Ausschluss' : bucket;

    setFormData(prev => ({
      ...prev,
      finalScore: totalScore,
      decisionBucket: bucket,
      finalDecision: decision
    }));
  }, [
    formData.scoreEdgeStrength, formData.scoreQuality, formData.scoreGrowthLeverage, formData.scoreSatelliteFit,
    formData.gateUniverseLiquidity, formData.gateRunway, formData.gateEdgeProof,
    formData.gateGrowthConvexity, formData.gateGovernance, formData.gateTradingFeasibility
  ]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: null }));
  };

  const handleScoreChange = (field, value, max) => {
    let numValue = parseInt(value, 10);
    if (isNaN(numValue)) numValue = 0;
    if (numValue < 0) numValue = 0;
    if (numValue > max) numValue = max;
    handleChange(field, numValue);
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.ticker?.trim()) newErrors.ticker = 'Ticker ist erforderlich';
    if (!formData.companyName?.trim()) newErrors.companyName = 'Unternehmen ist erforderlich';
    if (!formData.assetType) newErrors.assetType = 'Asset-Typ ist erforderlich';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) {
      toast.error('Bitte füllen Sie alle Pflichtfelder korrekt aus.');
      setActiveTab('stammdaten');
      return;
    }

    setIsSubmitting(true);
    try {
      const dataToSave = { ...formData, userId: pb.authStore.model.id };
      if (analysis?.id) {
        await pb.collection('analyses').update(analysis.id, dataToSave, { $autoCancel: false });
        toast.success('Analyse aktualisiert');
      } else {
        await pb.collection('analyses').create(dataToSave, { $autoCancel: false });
        toast.success('Analyse erstellt');
      }
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error saving analysis:', error);
      toast.error(error.response?.message || 'Fehler beim Speichern der Analyse');
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Auto-Calculation Logic ---
  const processBaseData = (data) => {
    let updates = { ...data, baseDataJson: JSON.stringify(data, null, 2) };
    let notes = [];
    
    // 1. Map basic fields if present
    if (data.ticker && !formData.ticker) updates.ticker = data.ticker;
    if (data.companyName && !formData.companyName) updates.companyName = data.companyName;
    if (data.assetType && !formData.assetType) updates.assetType = data.assetType;
    
    // 2. Auto-Gates
    // Universe & Liquidity
    if (data.exchange || data.marketCap || data.avgDollarVolume || data.spreadPct) {
      const validExchanges = ['NYSE', 'NASDAQ', 'Xetra', 'Euronext'];
      const isExchangeValid = data.exchange ? validExchanges.includes(data.exchange) : true;
      let fails = 0;
      if (data.marketCap && data.marketCap < 1e9) fails++;
      if (data.avgDollarVolume && data.avgDollarVolume < 1e7) fails++;
      if (data.spreadPct && data.spreadPct > 0.30) fails++;
      
      if (!isExchangeValid || fails >= 2) {
        updates.gateUniverseLiquidity = 'FAIL';
        notes.push('Liquidity: FAIL (Börse ungültig oder Schwellen verfehlt)');
      } else if (isExchangeValid && data.marketCap >= 1e9 && data.avgDollarVolume >= 1e7 && data.spreadPct <= 0.30) {
        updates.gateUniverseLiquidity = 'PASS';
        notes.push('Liquidity: PASS (Alle Kriterien erfüllt)');
      }
    }

    // Runway
    if (data.netCashFlag === true || (data.ttmFcf && data.ttmFcf > 0) || (data.runwayMonths && data.runwayMonths >= 18)) {
      updates.gateRunway = 'PASS';
      notes.push('Runway: PASS (Cash/FCF positiv oder Runway >= 18M)');
    }

    // Growth
    if (data.revenueCagr3y !== undefined && data.marginTrend) {
      if (data.revenueCagr3y >= 10 && ['stabil', 'verbessernd'].includes(data.marginTrend)) {
        updates.gateGrowthConvexity = 'PASS';
        notes.push('Growth: PASS (CAGR >= 10% & Margen stabil/besser)');
      }
    }

    // Trading Feasibility
    if (data.daysToEarnings !== undefined || data.avgDollarVolume || data.spreadPct) {
      if ((data.daysToEarnings !== undefined && data.daysToEarnings < 7) || 
          (data.avgDollarVolume && data.avgDollarVolume < 1e7) || 
          (data.spreadPct && data.spreadPct > 0.30)) {
        updates.gateTradingFeasibility = 'FAIL';
        notes.push('Trading: FAIL (Earnings nah, Volumen gering oder Spread hoch)');
      } else if ((data.daysToEarnings === undefined || data.daysToEarnings >= 7) && 
                 data.avgDollarVolume >= 1e7 && data.spreadPct <= 0.30) {
        updates.gateTradingFeasibility = 'PASS';
        notes.push('Trading: PASS (Kriterien erfüllt)');
      }
    }

    // 3. Auto-Scores
    let qScore = 0;
    if (data.ttmFcf > 0) qScore += 10;
    if (data.netCashFlag) qScore += 10;
    if (data.dilutionTrend === 'niedrig') qScore += 5;
    else if (data.dilutionTrend === 'stabil') qScore += 3;
    updates.scoreQuality = qScore;

    let gScore = 0;
    if (data.revenueCagr3y >= 20) gScore += 15;
    else if (data.revenueCagr3y >= 10) gScore += 10;
    if (data.marginTrend === 'verbessernd') gScore += 10;
    else if (data.marginTrend === 'stabil') gScore += 5;
    updates.scoreGrowthLeverage = gScore;

    let sScore = 0;
    if (data.avgDollarVolume >= 5e7) sScore += 8;
    else if (data.avgDollarVolume >= 1e7) sScore += 5;
    if (data.spreadPct <= 0.1) sScore += 6;
    else if (data.spreadPct <= 0.3) sScore += 3;
    if (data.volatilityBucket === 'low' || data.volatilityBucket === 'niedrig') sScore += 6;
    updates.scoreSatelliteFit = sScore;

    updates.autoDataStatus = 'Erfolgreich geladen';
    updates.autoDataNote = notes.join('\n');
    
    setFormData(prev => ({ ...prev, ...updates }));
    toast.success('Basisdaten erfolgreich verarbeitet');
  };

  const handleBaseDataImport = () => {
    try {
      const parsed = JSON.parse(baseDataInput);
      processBaseData(parsed);
      setActiveTab('basisdaten');
    } catch (e) {
      toast.error('Ungültiges JSON Format für Basisdaten');
    }
  };

  const handleResearchImport = () => {
    try {
      const parsed = JSON.parse(researchInput);
      let updates = { researchJson: JSON.stringify(parsed, null, 2) };
      let notes = formData.gateNotes ? formData.gateNotes + '\n\n--- Research Import ---\n' : '--- Research Import ---\n';

      if (parsed.qualitative_gates) {
        if (parsed.qualitative_gates.edge_proof) {
          updates.gateEdgeProof = parsed.qualitative_gates.edge_proof.status;
          notes += `Edge-Proof: ${parsed.qualitative_gates.edge_proof.reason}\n`;
        }
        if (parsed.qualitative_gates.governance) {
          updates.gateGovernance = parsed.qualitative_gates.governance.status;
          notes += `Governance: ${parsed.qualitative_gates.governance.reason}\n`;
        }
      }

      if (parsed.qualitative_scores?.edge_strength_override) {
        updates.scoreEdgeStrength = parsed.qualitative_scores.edge_strength_override.value;
      }

      if (parsed.summary) {
        if (parsed.summary.thesis) updates.thesis = parsed.summary.thesis;
        if (parsed.summary.catalyst) updates.catalyst = parsed.summary.catalyst;
        if (parsed.summary.risks) updates.risk = parsed.summary.risks;
      }

      if (parsed.optional_overrides) {
        if (parsed.optional_overrides.gateRunwayStatus) updates.gateRunway = parsed.optional_overrides.gateRunwayStatus;
        if (parsed.optional_overrides.scoreQuality) updates.scoreQuality = parsed.optional_overrides.scoreQuality;
      }

      updates.gateNotes = notes;
      setFormData(prev => ({ ...prev, ...updates }));
      toast.success('Research Daten erfolgreich importiert');
      setActiveTab('qualitativ');
    } catch (e) {
      toast.error('Ungültiges JSON Format für Research Daten');
    }
  };

  const generatePrompt = () => {
    const prompt = `Bitte analysiere das folgende Asset und liefere qualitative Einschätzungen.
Asset: ${formData.ticker} (${formData.companyName})
Typ: ${formData.assetType}

Fokus-Themen:
1. Edge-Proof: Gibt es Bottlenecks, Switching Costs, Netzwerkeffekte oder regulatorische Vorteile?
2. Governance: Gibt es Red Flags beim Management oder der Aktionärsstruktur?
3. Zusammenfassung: These, Katalysatoren, Risiken.

WICHTIG: Errate keine quantitativen Daten (wie KGV, FCF), die nicht gefragt sind.
Antworte AUSSCHLIESSLICH im folgenden JSON-Format:
{
  "asset": {"ticker": "${formData.ticker}", "name": "${formData.companyName}"},
  "qualitative_gates": {
    "edge_proof": {"status": "PASS|FAIL|OFFEN", "reason": "kurze Begründung", "evidence": ["punkt 1"]},
    "governance": {"status": "PASS|FAIL|OFFEN", "reason": "kurze Begründung", "evidence": []}
  },
  "qualitative_scores": {
    "edge_strength_override": {"value": 0-30, "max": 30, "reason": "Begründung für Score"}
  },
  "summary": {
    "thesis": "Investment These",
    "catalyst": "Katalysatoren",
    "risks": "Risiken",
    "management_quality": "...",
    "regulatory_context": "..."
  }
}`;
    setFormData(prev => ({ ...prev, researchPrompt: prompt }));
    navigator.clipboard.writeText(prompt);
    setCopiedPrompt(true);
    setTimeout(() => setCopiedPrompt(false), 2000);
    toast.success('Prompt generiert und in die Zwischenablage kopiert');
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[95vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="px-6 py-4 border-b bg-muted/10 shrink-0">
          <DialogTitle>{analysis ? 'Analyse bearbeiten' : 'Neue Analyse'}</DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 overflow-hidden flex flex-col">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <div className="px-6 pt-2 border-b shrink-0">
              <TabsList className="w-full justify-start h-auto flex-wrap gap-2 bg-transparent p-0">
                <TabsTrigger value="stammdaten" className="data-[state=active]:bg-muted">Stammdaten</TabsTrigger>
                <TabsTrigger value="basisdaten" className="data-[state=active]:bg-muted">Basisdaten (Auto)</TabsTrigger>
                <TabsTrigger value="gates_scores" className="data-[state=active]:bg-muted">Gates & Scores</TabsTrigger>
                <TabsTrigger value="qualitativ" className="data-[state=active]:bg-muted">Qualitativ</TabsTrigger>
                <TabsTrigger value="import" className="data-[state=active]:bg-muted">Import / AI</TabsTrigger>
              </TabsList>
            </div>

            <ScrollArea className="flex-1 p-6">
              <form id="analysis-form" onSubmit={handleSubmit} className="space-y-6">
                
                {/* TAB 1: Stammdaten */}
                <TabsContent value="stammdaten" className="m-0 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="ticker">Ticker *</Label>
                      <Input id="ticker" value={formData.ticker} onChange={(e) => handleChange('ticker', e.target.value.toUpperCase())} className={errors.ticker ? 'border-destructive' : ''} />
                      {errors.ticker && <p className="text-xs text-destructive">{errors.ticker}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="companyName">Unternehmen *</Label>
                      <Input id="companyName" value={formData.companyName} onChange={(e) => handleChange('companyName', e.target.value)} className={errors.companyName ? 'border-destructive' : ''} />
                      {errors.companyName && <p className="text-xs text-destructive">{errors.companyName}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="assetType">Asset-Typ *</Label>
                      <Select value={formData.assetType} onValueChange={(val) => handleChange('assetType', val)}>
                        <SelectTrigger className={errors.assetType ? 'border-destructive' : ''}><SelectValue placeholder="Wählen" /></SelectTrigger>
                        <SelectContent>{ASSET_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                      </Select>
                      {errors.assetType && <p className="text-xs text-destructive">{errors.assetType}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="isin">ISIN</Label>
                      <Input id="isin" value={formData.isin} onChange={(e) => handleChange('isin', e.target.value.toUpperCase())} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="wkn">WKN</Label>
                      <Input id="wkn" value={formData.wkn} onChange={(e) => handleChange('wkn', e.target.value.toUpperCase())} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="analysisType">Analyse-Typ</Label>
                      <Select value={formData.analysisType} onValueChange={(val) => handleChange('analysisType', val)}>
                        <SelectTrigger><SelectValue placeholder="Optional" /></SelectTrigger>
                        <SelectContent>{ANALYSIS_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                </TabsContent>

                {/* TAB 2: Basisdaten */}
                <TabsContent value="basisdaten" className="m-0 space-y-6">
                  <div className="bg-muted/30 p-4 rounded-lg border border-dashed">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-medium flex items-center gap-2"><Database className="h-4 w-4"/> Automatisch geladene Daten</h3>
                      <Badge variant="outline">{formData.autoDataStatus || 'Keine Daten'}</Badge>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div className="space-y-1"><Label className="text-xs text-muted-foreground">Börse</Label><Input value={formData.exchange} disabled className="h-8 bg-muted/50" /></div>
                      <div className="space-y-1"><Label className="text-xs text-muted-foreground">Sektor</Label><Input value={formData.sector} disabled className="h-8 bg-muted/50" /></div>
                      <div className="space-y-1"><Label className="text-xs text-muted-foreground">Market Cap</Label><Input value={formData.marketCap} disabled className="h-8 bg-muted/50" /></div>
                      <div className="space-y-1"><Label className="text-xs text-muted-foreground">Ø Volumen</Label><Input value={formData.avgDollarVolume} disabled className="h-8 bg-muted/50" /></div>
                      <div className="space-y-1"><Label className="text-xs text-muted-foreground">Spread %</Label><Input value={formData.spreadPct} disabled className="h-8 bg-muted/50" /></div>
                      <div className="space-y-1"><Label className="text-xs text-muted-foreground">TTM FCF</Label><Input value={formData.ttmFcf} disabled className="h-8 bg-muted/50" /></div>
                      <div className="space-y-1"><Label className="text-xs text-muted-foreground">Net Cash</Label><Input value={formData.netCashFlag ? 'Ja' : 'Nein'} disabled className="h-8 bg-muted/50" /></div>
                      <div className="space-y-1"><Label className="text-xs text-muted-foreground">Rev CAGR 3Y</Label><Input value={formData.revenueCagr3y} disabled className="h-8 bg-muted/50" /></div>
                    </div>
                    {formData.autoDataNote && (
                      <div className="mt-4 pt-4 border-t border-dashed">
                        <Label className="text-xs text-muted-foreground">Auto-Fill Notizen</Label>
                        <p className="text-xs mt-1 whitespace-pre-wrap text-muted-foreground">{formData.autoDataNote}</p>
                      </div>
                    )}
                  </div>
                </TabsContent>

                {/* TAB 3: Gates & Scores */}
                <TabsContent value="gates_scores" className="m-0 space-y-8">
                  <section className="space-y-4">
                    <h3 className="text-lg font-semibold border-b pb-2">Hard Gates</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {GATES.map(gate => (
                        <div key={gate.key} className="flex items-center justify-between bg-muted/20 p-3 rounded-lg border">
                          <div className="pr-4">
                            <Label className="text-sm font-medium">{gate.label}</Label>
                            <p className="text-xs text-muted-foreground mt-0.5">{gate.help}</p>
                          </div>
                          <Select value={formData[gate.key]} onValueChange={(val) => handleChange(gate.key, val)}>
                            <SelectTrigger className="w-[100px] h-8"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {GATE_STATUS.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                            </SelectContent>
                          </Select>
                        </div>
                      ))}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="gateNotes">Gate Notizen</Label>
                      <Textarea id="gateNotes" value={formData.gateNotes} onChange={(e) => handleChange('gateNotes', e.target.value)} className="min-h-[80px]" />
                    </div>
                  </section>

                  <section className="space-y-4">
                    <h3 className="text-lg font-semibold border-b pb-2">Score-Blöcke</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {SCORES.map(score => (
                        <div key={score.key} className="bg-muted/20 p-4 rounded-lg border text-center space-y-2">
                          <Label className="block text-sm font-medium">{score.label}</Label>
                          <p className="text-xs text-muted-foreground">Max: {score.max}</p>
                          <Input 
                            type="number" min="0" max={score.max}
                            value={formData[score.key]} 
                            onChange={(e) => handleScoreChange(score.key, e.target.value, score.max)}
                            className="text-center text-lg font-semibold h-10"
                          />
                        </div>
                      ))}
                    </div>
                  </section>
                </TabsContent>

                {/* TAB 4: Qualitativ */}
                <TabsContent value="qualitativ" className="m-0 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="thesis">These</Label>
                      <Textarea id="thesis" value={formData.thesis} onChange={(e) => handleChange('thesis', e.target.value)} className="min-h-[150px]" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="summary">Summary</Label>
                      <Textarea id="summary" value={formData.summary} onChange={(e) => handleChange('summary', e.target.value)} className="min-h-[150px]" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="risk">Risiko</Label>
                      <Textarea id="risk" value={formData.risk} onChange={(e) => handleChange('risk', e.target.value)} className="min-h-[150px]" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="catalyst">Katalysator</Label>
                      <Textarea id="catalyst" value={formData.catalyst} onChange={(e) => handleChange('catalyst', e.target.value)} className="min-h-[150px]" />
                    </div>
                  </div>
                </TabsContent>

                {/* TAB 5: Import / AI */}
                <TabsContent value="import" className="m-0 space-y-8">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Base Data Import */}
                    <div className="space-y-4 bg-muted/20 p-4 rounded-xl border">
                      <div className="flex items-center gap-2 border-b pb-2">
                        <Database className="h-5 w-5 text-primary" />
                        <h3 className="font-semibold">Basisdaten JSON Import</h3>
                      </div>
                      <p className="text-xs text-muted-foreground">Fügen Sie hier Rohdaten im JSON-Format ein, um Basisdaten, Gates und Scores automatisch vorzubefüllen.</p>
                      <Textarea 
                        value={baseDataInput} 
                        onChange={(e) => setBaseDataInput(e.target.value)} 
                        placeholder='{"ticker": "AAPL", "marketCap": 3000000000000, ...}'
                        className="font-mono text-xs min-h-[150px]"
                      />
                      <Button type="button" onClick={handleBaseDataImport} variant="secondary" className="w-full">
                        Basisdaten laden & verarbeiten
                      </Button>
                    </div>

                    {/* Research Import */}
                    <div className="space-y-4 bg-muted/20 p-4 rounded-xl border">
                      <div className="flex items-center gap-2 border-b pb-2">
                        <BrainCircuit className="h-5 w-5 text-primary" />
                        <h3 className="font-semibold">AI Research Import</h3>
                      </div>
                      <div className="flex justify-between items-center">
                        <p className="text-xs text-muted-foreground">Generieren Sie einen Prompt für LLMs und fügen Sie das Ergebnis hier ein.</p>
                        <Button type="button" size="sm" variant="outline" onClick={generatePrompt}>
                          {copiedPrompt ? <Check className="h-4 w-4 mr-2 text-green-500" /> : <Copy className="h-4 w-4 mr-2" />}
                          Prompt kopieren
                        </Button>
                      </div>
                      {formData.researchPrompt && (
                        <div className="bg-background border rounded p-2 text-xs font-mono text-muted-foreground max-h-[100px] overflow-y-auto">
                          {formData.researchPrompt}
                        </div>
                      )}
                      <Textarea 
                        value={researchInput} 
                        onChange={(e) => setResearchInput(e.target.value)} 
                        placeholder='{"qualitative_gates": {...}, "summary": {...}}'
                        className="font-mono text-xs min-h-[150px]"
                      />
                      <Button type="button" onClick={handleResearchImport} variant="secondary" className="w-full">
                        Research JSON importieren
                      </Button>
                    </div>
                  </div>
                </TabsContent>

              </form>
            </ScrollArea>

            {/* Sticky Footer with Live Results */}
            <div className="p-4 border-t bg-background shrink-0">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-6 bg-secondary/20 px-6 py-3 rounded-xl border border-secondary/30 w-full md:w-auto">
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">Score</p>
                    <p className="text-2xl font-bold">{formData.finalScore}</p>
                  </div>
                  <div className="w-px h-8 bg-border"></div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">Bucket</p>
                    <Badge variant="outline" className="mt-1">{formData.decisionBucket}</Badge>
                  </div>
                  <div className="w-px h-8 bg-border"></div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">Entscheidung</p>
                    <Badge variant={formData.finalDecision === 'Ausschluss' ? 'destructive' : 'default'} className="mt-1">
                      {formData.finalDecision}
                    </Badge>
                  </div>
                </div>
                
                <div className="flex gap-2 w-full md:w-auto">
                  <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting} className="flex-1 md:flex-none">
                    Abbrechen
                  </Button>
                  <Button type="submit" form="analysis-form" disabled={isSubmitting} className="flex-1 md:flex-none">
                    {isSubmitting ? 'Speichern...' : 'Analyse speichern'}
                  </Button>
                </div>
              </div>
            </div>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
}
