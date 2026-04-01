import React, { useEffect, useMemo, useState } from 'react';
import MainLayout from '@/components/layout/MainLayout.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { ArrowUpDown, BrainCircuit, Edit2, Eye, Inbox, Loader2, Plus, Search, Trash2 } from 'lucide-react';
import pb from '@/lib/pocketbaseClient';
import { toast } from 'sonner';
import AnalysisFormModal from '@/components/analyse/AnalysisFormModal.jsx';
import AnalysisDetailModal from '@/components/analyse/AnalysisDetailModal.jsx';

const normalizeDecision = (value) => {
  const raw = (value || '').toLowerCase().trim();
  if (['strong buy', 'buy', 'kaufkandidat'].includes(raw)) return 'Kaufkandidat';
  if (['booster-kandidat', 'booster candidate'].includes(raw)) return 'Booster-Kandidat';
  if (['hold', 'watch', 'watchlist'].includes(raw)) return 'Watchlist';
  if (['sell', 'exclude', 'ausschluss'].includes(raw)) return 'Ausschluss';
  if (['kein kandidat', 'no candidate', 'none'].includes(raw) || !raw) return 'kein Kandidat';
  return value;
};

export default function AnalysePage() {
  const [analyses, setAnalyses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [assetFilter, setAssetFilter] = useState('all');
  const [decisionFilter, setDecisionFilter] = useState('all');
  const [sortBy, setSortBy] = useState('updatedAt');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [analysisToDelete, setAnalysisToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchAnalyses = async () => {
    setIsLoading(true);
    try {
      const records = await pb.collection('analyses').getFullList({ sort: sortBy === 'finalScore' ? '-finalScore' : '-updatedAt', $autoCancel: false });
      setAnalyses(records);
    } catch {
      toast.error('Fehler beim Laden der Analysen.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, [sortBy]);

  const filteredAnalyses = useMemo(() => analyses.filter((item) => {
    const term = searchQuery.toLowerCase();
    const matchesSearch = !term || (item.ticker || '').toLowerCase().includes(term) || (item.companyName || '').toLowerCase().includes(term);
    const matchesAsset = assetFilter === 'all' || item.assetType === assetFilter;

    const normalizedBucket = normalizeDecision(item.decisionBucket);
    const normalizedDecision = normalizeDecision(item.finalDecision);
    const matchesDecision = decisionFilter === 'all' || normalizedBucket === decisionFilter || normalizedDecision === decisionFilter;

    return matchesSearch && matchesAsset && matchesDecision;
  }), [analyses, searchQuery, assetFilter, decisionFilter]);

  const openCreate = () => {
    setSelectedAnalysis(null);
    setIsFormOpen(true);
  };

  const openDetail = (item) => {
    setSelectedAnalysis(item);
    setIsDetailOpen(true);
  };

  const openEdit = (item) => {
    setSelectedAnalysis(item);
    setIsDetailOpen(false);
    setIsFormOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!analysisToDelete) return;
    setIsDeleting(true);
    try {
      await pb.collection('analyses').delete(analysisToDelete.id, { $autoCancel: false });
      toast.success('Analyse gelöscht.');
      setAnalysisToDelete(null);
      setIsDetailOpen(false);
      fetchAnalyses();
    } catch {
      toast.error('Fehler beim Löschen der Analyse.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <MainLayout title="Analyse">
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="bg-card border rounded-2xl p-6 shadow-sm flex flex-col md:flex-row justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2"><BrainCircuit className="h-8 w-8 text-primary" />Hybrid-Analyse</h1>
            <p className="text-muted-foreground mt-2">6 Hard Gates + 4 Score-Blöcke. Quantitative Teile kommen aus Basisdaten-Import, qualitative Teile aus Agent-Prompt + Research-JSON-Import.</p>
          </div>
          <Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" />Neue Analyse</Button>
        </div>

        <Card>
          <CardHeader className="border-b pb-4">
            <div className="flex flex-wrap gap-3 justify-between items-center">
              <CardTitle>Analysen Bestand</CardTitle>
              <div className="flex flex-wrap gap-2">
                <div className="relative min-w-[220px]"><Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" /><Input className="pl-8" placeholder="Ticker oder Name..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} /></div>
                <Select value={assetFilter} onValueChange={setAssetFilter}><SelectTrigger className="w-[130px]"><SelectValue placeholder="Asset" /></SelectTrigger><SelectContent><SelectItem value="all">Alle Typen</SelectItem><SelectItem value="Aktie">Aktie</SelectItem><SelectItem value="ETF">ETF</SelectItem><SelectItem value="Pennystock">Pennystock</SelectItem></SelectContent></Select>
                <Select value={decisionFilter} onValueChange={setDecisionFilter}><SelectTrigger className="w-[170px]"><SelectValue placeholder="Entscheidung" /></SelectTrigger><SelectContent><SelectItem value="all">Alle</SelectItem><SelectItem value="Booster-Kandidat">Booster-Kandidat</SelectItem><SelectItem value="Kaufkandidat">Kaufkandidat</SelectItem><SelectItem value="Watchlist">Watchlist</SelectItem><SelectItem value="Ausschluss">Ausschluss</SelectItem><SelectItem value="kein Kandidat">kein Kandidat</SelectItem></SelectContent></Select>
                <Button variant="outline" size="icon" title={sortBy === 'updatedAt' ? 'Sortierung: updatedAt' : 'Sortierung: finalScore'} onClick={() => setSortBy((prev) => (prev === 'updatedAt' ? 'finalScore' : 'updatedAt'))}><ArrowUpDown className="h-4 w-4" /></Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? <div className="py-12 text-center text-muted-foreground"><Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />Lade Analysen...</div> : filteredAnalyses.length === 0 ? <div className="py-14 text-center text-muted-foreground"><Inbox className="h-10 w-10 mx-auto mb-2" />Keine Analysen gefunden.</div> : (
              <Table>
                <TableHeader><TableRow><TableHead>Ticker</TableHead><TableHead>Unternehmen</TableHead><TableHead>Typ</TableHead><TableHead>Score</TableHead><TableHead>Bucket</TableHead><TableHead>Entscheidung</TableHead><TableHead className="text-right">Aktionen</TableHead></TableRow></TableHeader>
                <TableBody>
                  {filteredAnalyses.map((item) => (
                    <TableRow key={item.id} className="cursor-pointer" onClick={() => openDetail(item)}>
                      <TableCell>{item.ticker}</TableCell><TableCell>{item.companyName}</TableCell><TableCell>{item.assetType || '-'}</TableCell><TableCell>{item.finalScore || 0}</TableCell>
                      <TableCell><Badge variant="outline">{normalizeDecision(item.decisionBucket)}</Badge></TableCell>
                      <TableCell><Badge variant={normalizeDecision(item.finalDecision) === 'Ausschluss' ? 'destructive' : 'secondary'}>{normalizeDecision(item.finalDecision)}</Badge></TableCell>
                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" onClick={() => openDetail(item)}><Eye className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" onClick={() => openEdit(item)}><Edit2 className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" onClick={() => setAnalysisToDelete(item)}><Trash2 className="h-4 w-4" /></Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <AnalysisFormModal isOpen={isFormOpen} onClose={() => setIsFormOpen(false)} analysis={selectedAnalysis} onSuccess={fetchAnalyses} />
        <AnalysisDetailModal isOpen={isDetailOpen} onClose={() => setIsDetailOpen(false)} analysis={selectedAnalysis} onEdit={openEdit} onDelete={(a) => setAnalysisToDelete(a)} />

        <AlertDialog open={!!analysisToDelete} onOpenChange={(open) => !open && setAnalysisToDelete(null)}>
          <AlertDialogContent>
            <AlertDialogHeader><AlertDialogTitle>Analyse löschen?</AlertDialogTitle><AlertDialogDescription>Dieser Vorgang kann nicht rückgängig gemacht werden.</AlertDialogDescription></AlertDialogHeader>
            <AlertDialogFooter><AlertDialogCancel>Abbrechen</AlertDialogCancel><AlertDialogAction disabled={isDeleting} onClick={handleDeleteConfirm}>{isDeleting ? 'Lösche...' : 'Löschen'}</AlertDialogAction></AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </MainLayout>
  );
}
