import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table';
import { AlertTriangle, CheckCircle2, Edit2, HelpCircle, Trash2, XCircle } from 'lucide-react';
import { parseMetaBlock } from '@/lib/utils';

const GATES = [
  { key: 'gateUniverseLiquidityStatus', label: 'Universum & Liquidität' },
  { key: 'gateRunwayStatus', label: 'Runway 18-24M' },
  { key: 'gateEdgeProofStatus', label: 'Edge-Proof' },
  { key: 'gateGrowthConvexityStatus', label: 'Wachstum/Konvexität' },
  { key: 'gateGovernanceStatus', label: 'Governance' },
  { key: 'gateTradingFeasibilityStatus', label: 'Trading-Feasibility' }
];

const StatusIcon = ({ status }) => (
  status === 'PASS'
    ? <CheckCircle2 className="h-4 w-4 text-green-500" />
    : status === 'FAIL'
      ? <XCircle className="h-4 w-4 text-destructive" />
      : <HelpCircle className="h-4 w-4 text-yellow-500" />
);

export default function AnalysisDetailModal({ isOpen, onClose, analysis, onEdit, onDelete }) {
  if (!analysis) return null;

  const gateParts = parseMetaBlock(analysis.gateNotes || '');
  const scoreParts = parseMetaBlock(analysis.scoreNotes || '');
  const gateMeta = gateParts.meta || {};
  const scoreMeta = scoreParts.meta || {};

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl w-[96vw] h-[90vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="p-4 border-b bg-muted/10 flex flex-row items-center justify-between">
          <div>
            <DialogTitle className="text-2xl">{analysis.ticker} <Badge variant="outline">{analysis.assetType || '-'}</Badge></DialogTitle>
            <p className="text-muted-foreground text-sm">{analysis.companyName}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => onEdit(analysis)}><Edit2 className="h-4 w-4 mr-2" />Bearbeiten</Button>
            <Button variant="destructive" size="sm" onClick={() => onDelete(analysis)}><Trash2 className="h-4 w-4 mr-2" />Löschen</Button>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="border rounded p-4 text-center"><p className="text-xs text-muted-foreground">Final Score</p><p className="text-3xl font-bold">{analysis.finalScore || 0}</p></div>
            <div className="border rounded p-4 text-center"><p className="text-xs text-muted-foreground">Decision Bucket</p><Badge variant="outline">{analysis.decisionBucket || '-'}</Badge></div>
            <div className="border rounded p-4 text-center">
              <p className="text-xs text-muted-foreground">Final Decision</p>
              <Badge variant={analysis.finalDecision === 'Ausschluss' ? 'destructive' : 'secondary'}>{analysis.finalDecision || '-'}</Badge>
              {analysis.finalDecision === 'Ausschluss' && <p className="text-xs text-destructive mt-2 inline-flex items-center gap-1"><AlertTriangle className="h-3 w-3" />Gate-Ausschluss</p>}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="border rounded p-3"><p className="text-xs text-muted-foreground">ISIN</p><p className="text-sm">{gateMeta.isin || '-'}</p></div>
            <div className="border rounded p-3"><p className="text-xs text-muted-foreground">WKN</p><p className="text-sm">{gateMeta.wkn || '-'}</p></div>
            <div className="border rounded p-3"><p className="text-xs text-muted-foreground">Analyse-Typ</p><p className="text-sm">{gateMeta.analysisType || '-'}</p></div>
            <div className="border rounded p-3"><p className="text-xs text-muted-foreground">Bevorzugtes Importformat</p><p className="text-sm">{gateMeta.importFormatPreference || 'JSON'}</p></div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="border rounded p-4">
              <h3 className="font-semibold mb-3">Gates</h3>
              <Table>
                <TableBody>
                  {GATES.map((g) => (
                    <TableRow key={g.key}>
                      <TableCell>{g.label}</TableCell>
                      <TableCell className="text-right">
                        <span className="inline-flex items-center gap-2">{analysis[g.key] || 'OFFEN'}<StatusIcon status={analysis[g.key]} /></span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <p className="text-xs text-muted-foreground whitespace-pre-wrap mt-3">{gateParts.visibleText || 'Keine sichtbaren Gate-Notizen.'}</p>
            </div>

            <div className="border rounded p-4">
              <h3 className="font-semibold mb-2">Scores</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>Edge: <strong>{analysis.scoreEdgeStrength || 0}/30</strong></div>
                <div>Qualität: <strong>{analysis.scoreQuality || 0}/25</strong></div>
                <div>Growth: <strong>{analysis.scoreGrowthLeverage || 0}/25</strong></div>
                <div>Satellite: <strong>{analysis.scoreSatelliteFit || 0}/20</strong></div>
              </div>
              <p className="text-xs text-muted-foreground whitespace-pre-wrap mt-3">{scoreParts.visibleText || 'Keine sichtbaren Score-Notizen.'}</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="border rounded p-3"><p className="text-xs text-muted-foreground">These</p><p className="text-sm whitespace-pre-wrap">{analysis.thesis || '-'}</p></div>
            <div className="border rounded p-3"><p className="text-xs text-muted-foreground">Summary</p><p className="text-sm whitespace-pre-wrap">{analysis.summary || '-'}</p></div>
            <div className="border rounded p-3"><p className="text-xs text-muted-foreground">Risiko</p><p className="text-sm whitespace-pre-wrap">{analysis.risk || '-'}</p></div>
            <div className="border rounded p-3"><p className="text-xs text-muted-foreground">Katalysator</p><p className="text-sm whitespace-pre-wrap">{analysis.catalyst || '-'}</p></div>
          </div>

          <details className="border rounded p-3">
            <summary className="cursor-pointer text-sm font-medium">Generierter Prompt</summary>
            <pre className="text-xs mt-2 whitespace-pre-wrap break-words">{scoreMeta.generatedPrompt || 'Nicht vorhanden.'}</pre>
          </details>

          <details className="border rounded p-3">
            <summary className="cursor-pointer text-sm font-medium">Importiertes Roh-JSON</summary>
            <pre className="text-xs mt-2 whitespace-pre-wrap break-words">{scoreMeta.importedRawPayload || 'Nicht vorhanden.'}</pre>
            <p className="text-xs text-muted-foreground mt-2">Format: {scoreMeta.importedPayloadFormat || '-'} · Letzter Import: {scoreMeta.lastImportAt || '-'}</p>
          </details>
        </div>
      </DialogContent>
    </Dialog>
  );
}
