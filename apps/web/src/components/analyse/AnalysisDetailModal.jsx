
import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Edit2, Trash2, AlertTriangle, CheckCircle2, XCircle, HelpCircle, Database, FileJson, BrainCircuit } from 'lucide-react';

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

const StatusIcon = ({ status }) => {
  if (status === 'PASS') return <CheckCircle2 className="h-5 w-5 text-green-500" />;
  if (status === 'FAIL') return <XCircle className="h-5 w-5 text-destructive" />;
  return <HelpCircle className="h-5 w-5 text-yellow-500" />;
};

const StatusBadge = ({ status }) => {
  if (status === 'PASS') return <Badge className="bg-green-100 text-green-800 hover:bg-green-100/80 dark:bg-green-900/30 dark:text-green-300">PASS</Badge>;
  if (status === 'FAIL') return <Badge variant="destructive">FAIL</Badge>;
  return <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100/80 dark:bg-yellow-900/30 dark:text-yellow-300">OFFEN</Badge>;
};

const DataRow = ({ label, value, suffix = '' }) => (
  <div className="flex justify-between py-1 border-b border-border/50 last:border-0">
    <span className="text-muted-foreground text-sm">{label}</span>
    <span className="font-medium text-sm text-right">
      {value !== null && value !== undefined && value !== '' ? `${value}${suffix}` : '-'}
    </span>
  </div>
);

export default function AnalysisDetailModal({ isOpen, onClose, analysis, onEdit, onDelete }) {
  if (!analysis) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[90vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="px-6 py-4 border-b bg-muted/10 flex flex-row items-start justify-between shrink-0">
          <div>
            <DialogTitle className="text-2xl flex items-center gap-3">
              {analysis.ticker}
              <Badge variant="outline" className="text-sm font-normal">{analysis.assetType}</Badge>
              {analysis.analysisType && <Badge variant="secondary" className="text-xs font-normal">{analysis.analysisType}</Badge>}
            </DialogTitle>
            <p className="text-muted-foreground mt-1">{analysis.companyName}</p>
            <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
              {analysis.isin && <span>ISIN: {analysis.isin}</span>}
              {analysis.wkn && <span>WKN: {analysis.wkn}</span>}
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => onEdit(analysis)}>
              <Edit2 className="h-4 w-4 mr-2" />
              Bearbeiten
            </Button>
            <Button variant="destructive" size="sm" onClick={() => onDelete(analysis)}>
              <Trash2 className="h-4 w-4 mr-2" />
              Löschen
            </Button>
          </div>
        </DialogHeader>

        <ScrollArea className="flex-1 p-6">
          <div className="space-y-8 pb-8">
            {/* Header KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-card border rounded-xl p-4 text-center shadow-sm">
                <p className="text-sm text-muted-foreground mb-1">Final Score</p>
                <p className="text-4xl font-bold">{analysis.finalScore || 0} <span className="text-lg text-muted-foreground font-normal">/ 100</span></p>
              </div>
              <div className="bg-card border rounded-xl p-4 text-center shadow-sm flex flex-col items-center justify-center">
                <p className="text-sm text-muted-foreground mb-2">Decision Bucket</p>
                <Badge variant="secondary" className="text-base py-1 px-3">{analysis.decisionBucket || 'Ausstehend'}</Badge>
              </div>
              <div className="bg-card border rounded-xl p-4 text-center shadow-sm flex flex-col items-center justify-center">
                <p className="text-sm text-muted-foreground mb-2">Finale Entscheidung</p>
                <Badge 
                  variant={analysis.finalDecision === 'Ausschluss' ? 'destructive' : 'default'} 
                  className="text-base py-1 px-3"
                >
                  {analysis.finalDecision || 'Ausstehend'}
                </Badge>
                {analysis.finalDecision === 'Ausschluss' && (
                  <p className="text-xs text-destructive mt-2 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Gate-Ausschluss
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left Column: Basisdaten */}
              <div className="space-y-6 lg:col-span-1">
                <div className="bg-muted/20 border rounded-xl p-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4 flex items-center gap-2">
                    <Database className="h-4 w-4" />
                    Basisdaten
                  </h3>
                  <div className="space-y-1">
                    <DataRow label="Börse" value={analysis.exchange} />
                    <DataRow label="Land" value={analysis.country} />
                    <DataRow label="Sektor" value={analysis.sector} />
                    <DataRow label="Währung" value={analysis.currency} />
                    <DataRow label="Preis" value={analysis.price} />
                    <DataRow label="Market Cap" value={analysis.marketCap ? (analysis.marketCap / 1e9).toFixed(2) : null} suffix=" Mrd" />
                    <DataRow label="Ø Volumen" value={analysis.avgDollarVolume ? (analysis.avgDollarVolume / 1e6).toFixed(2) : null} suffix=" Mio" />
                    <DataRow label="Spread" value={analysis.spreadPct} suffix="%" />
                    <DataRow label="TTM FCF" value={analysis.ttmFcf ? (analysis.ttmFcf / 1e6).toFixed(2) : null} suffix=" Mio" />
                    <DataRow label="Net Cash" value={analysis.netCashFlag !== undefined ? (analysis.netCashFlag ? 'Ja' : 'Nein') : null} />
                    <DataRow label="Runway" value={analysis.runwayMonths} suffix=" Mon" />
                    <DataRow label="Rev CAGR 3Y" value={analysis.revenueCagr3y} suffix="%" />
                    <DataRow label="Margin Trend" value={analysis.marginTrend} />
                    <DataRow label="Dilution Trend" value={analysis.dilutionTrend} />
                    <DataRow label="Volatility" value={analysis.volatilityBucket} />
                    {analysis.assetType === 'ETF' && (
                      <>
                        <DataRow label="TER" value={analysis.terPct} suffix="%" />
                        <DataRow label="Domizil" value={analysis.domicile} />
                        <DataRow label="Replikation" value={analysis.replicationMethod} />
                        <DataRow label="Tracking Diff" value={analysis.trackingDifferencePct} suffix="%" />
                      </>
                    )}
                  </div>
                  {analysis.autoDataStatus && (
                    <div className="mt-4 pt-4 border-t">
                      <Badge variant="outline" className="mb-2">{analysis.autoDataStatus}</Badge>
                      {analysis.autoDataNote && (
                        <p className="text-xs text-muted-foreground whitespace-pre-wrap">{analysis.autoDataNote}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Gates & Scores */}
              <div className="space-y-8 lg:col-span-2">
                {/* Gates */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold border-b pb-2">Hard Gates</h3>
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableBody>
                        {GATES.map(gate => (
                          <TableRow key={gate.key}>
                            <TableCell className="font-medium w-1/2">{gate.label}</TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-2">
                                <StatusBadge status={analysis[gate.key]} />
                                <StatusIcon status={analysis[gate.key]} />
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {analysis.gateNotes && (
                    <div className="bg-muted/30 p-3 rounded-lg text-sm">
                      <span className="font-semibold block mb-1">Gate Notizen:</span>
                      <p className="text-muted-foreground whitespace-pre-wrap">{analysis.gateNotes}</p>
                    </div>
                  )}
                </div>

                {/* Scores */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold border-b pb-2">Score-Blöcke</h3>
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader className="bg-muted/50">
                        <TableRow>
                          <TableHead>Kategorie</TableHead>
                          <TableHead className="text-right">Score</TableHead>
                          <TableHead className="text-right">Max</TableHead>
                          <TableHead className="text-right">%</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {SCORES.map(score => {
                          const val = analysis[score.key] || 0;
                          const pct = Math.round((val / score.max) * 100);
                          return (
                            <TableRow key={score.key}>
                              <TableCell className="font-medium">{score.label}</TableCell>
                              <TableCell className="text-right font-semibold">{val}</TableCell>
                              <TableCell className="text-right text-muted-foreground">{score.max}</TableCell>
                              <TableCell className="text-right text-muted-foreground">{pct}%</TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              </div>
            </div>

            {/* Content Sections */}
            <div className="space-y-6 pt-4">
              <h3 className="text-lg font-semibold border-b pb-2 flex items-center gap-2">
                <BrainCircuit className="h-5 w-5" />
                Qualitative Analyse
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">These</h4>
                  <div className="bg-card border rounded-lg p-4 min-h-[100px] whitespace-pre-wrap text-sm">
                    {analysis.thesis || <span className="text-muted-foreground italic">Keine These hinterlegt.</span>}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">Summary</h4>
                  <div className="bg-card border rounded-lg p-4 min-h-[100px] whitespace-pre-wrap text-sm">
                    {analysis.summary || <span className="text-muted-foreground italic">Keine Summary hinterlegt.</span>}
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">Risiko</h4>
                  <div className="bg-card border rounded-lg p-4 min-h-[100px] whitespace-pre-wrap text-sm">
                    {analysis.risk || <span className="text-muted-foreground italic">Keine Risiken hinterlegt.</span>}
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">Katalysator</h4>
                  <div className="bg-card border rounded-lg p-4 min-h-[100px] whitespace-pre-wrap text-sm">
                    {analysis.catalyst || <span className="text-muted-foreground italic">Keine Katalysatoren hinterlegt.</span>}
                  </div>
                </div>
              </div>
            </div>

            {/* Meta / JSON Data */}
            {(analysis.baseDataJson || analysis.researchJson) && (
              <div className="space-y-4 pt-8 border-t">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <FileJson className="h-4 w-4" />
                  Rohdaten & Importe
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {analysis.baseDataJson && (
                    <div className="space-y-2">
                      <span className="text-xs font-medium">Basisdaten JSON</span>
                      <div className="bg-muted p-3 rounded-md text-xs font-mono overflow-x-auto max-h-[200px]">
                        <pre>{analysis.baseDataJson}</pre>
                      </div>
                    </div>
                  )}
                  {analysis.researchJson && (
                    <div className="space-y-2">
                      <span className="text-xs font-medium">Research JSON</span>
                      <div className="bg-muted p-3 rounded-md text-xs font-mono overflow-x-auto max-h-[200px]">
                        <pre>{analysis.researchJson}</pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
