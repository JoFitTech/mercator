import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertTriangle, BrainCircuit, CheckCircle2, Database, Edit2, HelpCircle, Trash2, XCircle } from 'lucide-react';

const GATES = [
  { key: 'gateUniverseLiquidity', label: 'Universum & Liquidität' },
  { key: 'gateRunway', label: 'Runway 18-24M' },
  { key: 'gateEdgeProof', label: 'Edge-Proof' },
  { key: 'gateGrowthConvexity', label: 'Wachstum/Konvexität' },
  { key: 'gateGovernance', label: 'Governance' },
  { key: 'gateTradingFeasibility', label: 'Trading-Feasibility' }
];

const StatusIcon = ({ status }) => (status === 'PASS' ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : status === 'FAIL' ? <XCircle className="h-4 w-4 text-destructive" /> : <HelpCircle className="h-4 w-4 text-yellow-500" />);
const DataRow = ({ label, value }) => <div className="flex justify-between py-1 border-b last:border-0"><span className="text-muted-foreground text-sm">{label}</span><span className="text-sm">{value || '-'}</span></div>;

export default function AnalysisDetailModal({ isOpen, onClose, analysis, onEdit, onDelete }) {
  if (!analysis) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[92vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="p-4 border-b bg-muted/10 flex flex-row items-center justify-between">
          <div>
            <DialogTitle className="text-2xl">{analysis.ticker} <Badge variant="outline">{analysis.assetType || '-'}</Badge></DialogTitle>
            <p className="text-muted-foreground text-sm">{analysis.companyName}</p>
            <p className="text-xs text-muted-foreground mt-1">ISIN: {analysis.isin || '-'} · WKN: {analysis.wkn || '-'} · Analyse-Typ: {analysis.analysisType || '-'}</p>
          </div>
          <div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => onEdit(analysis)}><Edit2 className="h-4 w-4 mr-2" />Bearbeiten</Button><Button variant="destructive" size="sm" onClick={() => onDelete(analysis)}><Trash2 className="h-4 w-4 mr-2" />Löschen</Button></div>
        </DialogHeader>

        <ScrollArea className="flex-1 p-6">
          <div className="space-y-6">
            <div className="grid md:grid-cols-3 gap-4">
              <div className="border rounded p-4 text-center"><p className="text-xs text-muted-foreground">Final Score</p><p className="text-3xl font-bold">{analysis.finalScore || 0}</p></div>
              <div className="border rounded p-4 text-center"><p className="text-xs text-muted-foreground">Decision Bucket</p><Badge variant="outline">{analysis.decisionBucket || '-'}</Badge></div>
              <div className="border rounded p-4 text-center"><p className="text-xs text-muted-foreground">Final Decision</p><Badge variant={analysis.finalDecision === 'Ausschluss' ? 'destructive' : 'secondary'}>{analysis.finalDecision || '-'}</Badge>{analysis.finalDecision === 'Ausschluss' && <p className="text-xs text-destructive mt-2 inline-flex items-center gap-1"><AlertTriangle className="h-3 w-3" />Gate-Ausschluss</p>}</div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <div className="border rounded p-4">
                <h3 className="font-semibold mb-3 flex items-center gap-2"><Database className="h-4 w-4" />Basisdaten & Auto-Fill</h3>
                <DataRow label="Börse" value={analysis.exchange} />
                <DataRow label="Land" value={analysis.country} />
                <DataRow label="Region" value={analysis.region} />
                <DataRow label="Sektor" value={analysis.sector} />
                <DataRow label="Währung" value={analysis.currency} />
                <DataRow label="Auto-Status" value={analysis.autoDataStatus} />
                <div className="mt-2 text-xs whitespace-pre-wrap text-muted-foreground">{analysis.autoDataNote || 'Keine Auto-Notiz vorhanden.'}</div>
              </div>
              <div className="border rounded p-4">
                <h3 className="font-semibold mb-3">Gates</h3>
                <Table><TableBody>{GATES.map((g) => <TableRow key={g.key}><TableCell>{g.label}</TableCell><TableCell className="text-right"><span className="inline-flex items-center gap-2">{analysis[g.key] || 'OFFEN'}<StatusIcon status={analysis[g.key]} /></span></TableCell></TableRow>)}</TableBody></Table>
                <p className="text-xs text-muted-foreground whitespace-pre-wrap mt-2">{analysis.gateNotes || 'Keine Gate-Notizen.'}</p>
              </div>
            </div>

            <div className="border rounded p-4">
              <h3 className="font-semibold mb-2">Scores</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>Edge: <strong>{analysis.scoreEdgeStrength || 0}/30</strong></div>
                <div>Qualität: <strong>{analysis.scoreQuality || 0}/25</strong></div>
                <div>Growth: <strong>{analysis.scoreGrowthLeverage || 0}/25</strong></div>
                <div>Satellite: <strong>{analysis.scoreSatelliteFit || 0}/20</strong></div>
              </div>
              <p className="text-xs text-muted-foreground whitespace-pre-wrap mt-2">{analysis.scoreNotes || 'Keine Score-Notizen.'}</p>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              <div className="border rounded p-3"><p className="text-xs text-muted-foreground">These</p><p className="text-sm whitespace-pre-wrap">{analysis.thesis || '-'}</p></div>
              <div className="border rounded p-3"><p className="text-xs text-muted-foreground">Risiko</p><p className="text-sm whitespace-pre-wrap">{analysis.risk || '-'}</p></div>
              <div className="border rounded p-3"><p className="text-xs text-muted-foreground">Katalysator</p><p className="text-sm whitespace-pre-wrap">{analysis.catalyst || '-'}</p></div>
            </div>

            <div className="space-y-3 border-t pt-4">
              <h3 className="font-semibold flex items-center gap-2"><BrainCircuit className="h-4 w-4" />Research Artefakte</h3>
              <details className="border rounded p-3"><summary className="cursor-pointer text-sm font-medium">Research Prompt anzeigen</summary><pre className="mt-2 text-xs whitespace-pre-wrap">{analysis.researchPrompt || 'Kein Prompt gespeichert.'}</pre></details>
              <details className="border rounded p-3"><summary className="cursor-pointer text-sm font-medium">Research JSON anzeigen</summary><pre className="mt-2 text-xs whitespace-pre-wrap">{analysis.researchJson || 'Kein Research-JSON gespeichert.'}</pre></details>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
