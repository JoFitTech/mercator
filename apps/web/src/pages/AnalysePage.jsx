
import React, { useState, useEffect, useMemo } from 'react';
import MainLayout from '@/components/layout/MainLayout.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Plus, Search, Edit2, Trash2, Loader2, Inbox, Eye, Database, BrainCircuit, FileJson, ArrowUpDown } from 'lucide-react';
import pb from '@/lib/pocketbaseClient';
import { toast } from 'sonner';
import AnalysisFormModal from '@/components/analyse/AnalysisFormModal.jsx';
import AnalysisDetailModal from '@/components/analyse/AnalysisDetailModal.jsx';

export default function AnalysePage() {
  const [analyses, setAnalyses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Filters & Sort
  const [searchQuery, setSearchQuery] = useState('');
  const [assetFilter, setAssetFilter] = useState('all');
  const [decisionFilter, setDecisionFilter] = useState('all');
  const [sortBy, setSortBy] = useState('updatedAt'); // 'updatedAt' or 'finalScore'
  
  // Modals State
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [formInitialTab, setFormInitialTab] = useState('stammdaten');
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  
  // Delete Dialog State
  const [analysisToDelete, setAnalysisToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchAnalyses = async () => {
    setIsLoading(true);
    try {
      const records = await pb.collection('analyses').getFullList({
        sort: sortBy === 'finalScore' ? '-finalScore' : '-updatedAt',
        $autoCancel: false
      });
      setAnalyses(records);
    } catch (error) {
      console.error('Error fetching analyses:', error);
      toast.error('Fehler beim Laden der Analysen');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, [sortBy]);

  const filteredAnalyses = useMemo(() => {
    return analyses.filter(item => {
      const matchesSearch = !searchQuery.trim() || 
        item.ticker.toLowerCase().includes(searchQuery.toLowerCase()) || 
        (item.companyName && item.companyName.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesAsset = assetFilter === 'all' || item.assetType === assetFilter;
      const matchesDecision = decisionFilter === 'all' || item.finalDecision === decisionFilter;
      
      return matchesSearch && matchesAsset && matchesDecision;
    });
  }, [analyses, searchQuery, assetFilter, decisionFilter]);

  const handleOpenCreate = (tab = 'stammdaten') => {
    setSelectedAnalysis(null);
    setFormInitialTab(tab);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (analysis) => {
    setSelectedAnalysis(analysis);
    setFormInitialTab('stammdaten');
    setIsDetailOpen(false);
    setIsFormOpen(true);
  };

  const handleOpenDetail = (analysis) => {
    setSelectedAnalysis(analysis);
    setIsDetailOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!analysisToDelete) return;
    setIsDeleting(true);
    try {
      await pb.collection('analyses').delete(analysisToDelete.id, { $autoCancel: false });
      toast.success('Analyse gelöscht');
      setIsDetailOpen(false);
      fetchAnalyses();
    } catch (error) {
      console.error('Error deleting analysis:', error);
      toast.error('Fehler beim Löschen der Analyse');
    } finally {
      setIsDeleting(false);
      setAnalysisToDelete(null);
    }
  };

  return (
    <MainLayout title="Analyse">
      <div className="space-y-6 max-w-7xl mx-auto">
        
        {/* ANALYSE-HEADER */}
        <div className="bg-card border rounded-2xl p-6 shadow-sm">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
            <div className="max-w-2xl">
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                <BrainCircuit className="h-8 w-8 text-primary" />
                Hybrid-Analyse
              </h1>
              <p className="text-muted-foreground mt-2 leading-relaxed">
                Kombinieren Sie quantitative Basisdaten mit qualitativen AI-Insights. 
                Nutzen Sie das Scoring-Modell und die Hard Gates, um objektive Investmententscheidungen zu treffen.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 w-full md:w-auto">
              <Button onClick={() => handleOpenCreate('stammdaten')} className="w-full">
                <Plus className="mr-2 h-4 w-4" /> Neue Analyse
              </Button>
              <Button onClick={() => handleOpenCreate('import')} variant="secondary" className="w-full">
                <Database className="mr-2 h-4 w-4" /> Basisdaten laden
              </Button>
              <Button onClick={() => handleOpenCreate('import')} variant="outline" className="w-full">
                <BrainCircuit className="mr-2 h-4 w-4" /> Prompt generieren
              </Button>
              <Button onClick={() => handleOpenCreate('import')} variant="outline" className="w-full">
                <FileJson className="mr-2 h-4 w-4" /> JSON importieren
              </Button>
            </div>
          </div>
        </div>

        {/* Table Section */}
        <Card className="shadow-sm">
          <CardHeader className="pb-4 border-b">
            <div className="flex flex-col lg:flex-row gap-4 justify-between items-start lg:items-center">
              <CardTitle>Analysen Bestand</CardTitle>
              
              <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
                <div className="relative flex-1 min-w-[200px]">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="search"
                    placeholder="Ticker oder Name..."
                    className="pl-9"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                
                <Select value={assetFilter} onValueChange={setAssetFilter}>
                  <SelectTrigger className="w-[130px]">
                    <SelectValue placeholder="Asset-Typ" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Typen</SelectItem>
                    <SelectItem value="Aktie">Aktie</SelectItem>
                    <SelectItem value="ETF">ETF</SelectItem>
                    <SelectItem value="Pennystock">Pennystock</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={decisionFilter} onValueChange={setDecisionFilter}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Entscheidung" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Status</SelectItem>
                    <SelectItem value="Booster-Kandidat">Booster</SelectItem>
                    <SelectItem value="Kaufkandidat">Kaufkandidat</SelectItem>
                    <SelectItem value="Watchlist">Watchlist</SelectItem>
                    <SelectItem value="Ausschluss">Ausschluss</SelectItem>
                  </SelectContent>
                </Select>

                <Button 
                  variant="outline" 
                  size="icon"
                  onClick={() => setSortBy(prev => prev === 'updatedAt' ? 'finalScore' : 'updatedAt')}
                  title={`Sortiert nach: ${sortBy === 'updatedAt' ? 'Datum' : 'Score'}`}
                >
                  <ArrowUpDown className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mb-4" />
                <p>Lade Analysen...</p>
              </div>
            ) : filteredAnalyses.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center bg-muted/10">
                <Inbox className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-medium">Keine Analysen gefunden</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                  Passen Sie Ihre Filter an oder erstellen Sie eine neue Analyse.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-muted/30">
                    <TableRow>
                      <TableHead className="w-[100px]">Ticker</TableHead>
                      <TableHead>Unternehmen</TableHead>
                      <TableHead className="hidden md:table-cell">ISIN</TableHead>
                      <TableHead>Typ</TableHead>
                      <TableHead className="text-center">Score</TableHead>
                      <TableHead className="hidden sm:table-cell">Bucket</TableHead>
                      <TableHead>Entscheidung</TableHead>
                      <TableHead className="text-right">Aktionen</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredAnalyses.map((item) => (
                      <TableRow key={item.id} className="group cursor-pointer hover:bg-muted/50" onClick={() => handleOpenDetail(item)}>
                        <TableCell className="font-medium">{item.ticker}</TableCell>
                        <TableCell className="max-w-[200px] truncate" title={item.companyName}>{item.companyName}</TableCell>
                        <TableCell className="hidden md:table-cell text-xs text-muted-foreground">{item.isin || '-'}</TableCell>
                        <TableCell className="text-muted-foreground text-sm">{item.assetType}</TableCell>
                        <TableCell className="text-center font-semibold">{item.finalScore || 0}</TableCell>
                        <TableCell className="hidden sm:table-cell">
                          <Badge variant="outline" className="font-normal text-xs">
                            {item.decisionBucket || '-'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge 
                            variant={item.finalDecision === 'Ausschluss' ? 'destructive' : 'secondary'} 
                            className="font-normal text-xs"
                          >
                            {item.finalDecision || '-'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenDetail(item)}>
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenEdit(item)}>
                              <Edit2 className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => setAnalysisToDelete(item)}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <AnalysisFormModal 
        isOpen={isFormOpen} 
        onClose={() => setIsFormOpen(false)} 
        analysis={selectedAnalysis}
        onSuccess={fetchAnalyses}
        initialTab={formInitialTab}
      />

      <AnalysisDetailModal
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        analysis={selectedAnalysis}
        onEdit={handleOpenEdit}
        onDelete={(item) => setAnalysisToDelete(item)}
      />

      <AlertDialog open={!!analysisToDelete} onOpenChange={(open) => !open && setAnalysisToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Analyse löschen?</AlertDialogTitle>
            <AlertDialogDescription>
              Möchten Sie die Analyse für <strong>{analysisToDelete?.ticker}</strong> wirklich löschen? 
              Dieser Vorgang kann nicht rückgängig gemacht werden.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Abbrechen</AlertDialogCancel>
            <AlertDialogAction 
              onClick={(e) => {
                e.preventDefault();
                handleDeleteConfirm();
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={isDeleting}
            >
              {isDeleting ? 'Wird gelöscht...' : 'Löschen'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </MainLayout>
  );
}
