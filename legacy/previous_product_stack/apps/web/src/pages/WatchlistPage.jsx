
import React, { useState, useEffect, useMemo } from 'react';
import MainLayout from '@/components/layout/MainLayout.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Plus, Search, Edit2, Trash2, Loader2, Inbox } from 'lucide-react';
import pb from '@/lib/pocketbaseClient';
import { toast } from 'sonner';
import WatchlistForm from '@/components/watchlist/WatchlistForm.jsx';

const getStatusBadgeColor = (status) => {
  switch (status) {
    case 'Beobachten':
      return 'bg-blue-100 text-blue-800 hover:bg-blue-100/80 dark:bg-blue-900/30 dark:text-blue-300';
    case 'Watchlist':
      return 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100/80 dark:bg-yellow-900/30 dark:text-yellow-300';
    case 'Kaufkandidat':
      return 'bg-green-100 text-green-800 hover:bg-green-100/80 dark:bg-green-900/30 dark:text-green-300';
    case 'Archiviert':
      return 'bg-gray-100 text-gray-800 hover:bg-gray-100/80 dark:bg-gray-800/50 dark:text-gray-300';
    default:
      return 'bg-secondary text-secondary-foreground';
  }
};

export default function WatchlistPage() {
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Form Modal State
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  
  // Delete Dialog State
  const [itemToDelete, setItemToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchItems = async () => {
    setIsLoading(true);
    try {
      const records = await pb.collection('watchlist_items').getFullList({
        sort: '-created',
        $autoCancel: false
      });
      setItems(records);
    } catch (error) {
      console.error('Error fetching watchlist:', error);
      toast.error('Fehler beim Laden der Watchlist');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const query = searchQuery.toLowerCase();
    return items.filter(item => 
      item.ticker.toLowerCase().includes(query) || 
      item.name.toLowerCase().includes(query)
    );
  }, [items, searchQuery]);

  const handleOpenCreate = () => {
    setEditingItem(null);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (item) => {
    setEditingItem(item);
    setIsFormOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!itemToDelete) return;
    
    setIsDeleting(true);
    try {
      await pb.collection('watchlist_items').delete(itemToDelete.id, { $autoCancel: false });
      toast.success('Eintrag gelöscht');
      fetchItems();
    } catch (error) {
      console.error('Error deleting item:', error);
      toast.error('Fehler beim Löschen des Eintrags');
    } finally {
      setIsDeleting(false);
      setItemToDelete(null);
    }
  };

  return (
    <MainLayout title="Watchlist">
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Watchlist</h1>
            <p className="text-muted-foreground mt-1">
              Beobachten und bewerten Sie potenzielle Investment-Kandidaten.
            </p>
          </div>
          <Button onClick={handleOpenCreate} className="w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" />
            Neuer Eintrag
          </Button>
        </div>

        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle>Einträge</CardTitle>
              <div className="relative w-full max-w-sm">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder="Suchen nach Ticker oder Name..."
                  className="pl-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mb-4" />
                <p>Lade Watchlist...</p>
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed rounded-lg bg-muted/30">
                <Inbox className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-medium">Keine Einträge gefunden</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                  {searchQuery 
                    ? 'Es wurden keine Einträge gefunden, die Ihrer Suche entsprechen.' 
                    : 'Ihre Watchlist ist leer. Fügen Sie neue Kandidaten hinzu, um sie zu beobachten.'}
                </p>
                {!searchQuery && (
                  <Button variant="outline" className="mt-6" onClick={handleOpenCreate}>
                    Ersten Eintrag erstellen
                  </Button>
                )}
              </div>
            ) : (
              <div className="rounded-md border overflow-hidden">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader className="bg-muted/50">
                      <TableRow>
                        <TableHead className="w-[100px]">Ticker</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Typ</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="hidden md:table-cell">Notiz</TableHead>
                        <TableHead className="text-right">Aktionen</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredItems.map((item) => (
                        <TableRow key={item.id} className="group">
                          <TableCell className="font-medium">{item.ticker}</TableCell>
                          <TableCell>{item.name}</TableCell>
                          <TableCell className="text-muted-foreground">{item.itemType}</TableCell>
                          <TableCell>
                            <Badge variant="secondary" className={`font-normal ${getStatusBadgeColor(item.status)}`}>
                              {item.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="hidden md:table-cell text-muted-foreground max-w-[300px] truncate">
                            {item.notes || '-'}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button 
                                variant="ghost" 
                                size="icon" 
                                className="h-8 w-8"
                                onClick={() => handleOpenEdit(item)}
                                aria-label="Bearbeiten"
                              >
                                <Edit2 className="h-4 w-4" />
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="icon" 
                                className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                onClick={() => setItemToDelete(item)}
                                aria-label="Löschen"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <WatchlistForm 
        isOpen={isFormOpen} 
        onClose={() => setIsFormOpen(false)} 
        item={editingItem}
        onSuccess={fetchItems}
      />

      <AlertDialog open={!!itemToDelete} onOpenChange={(open) => !open && setItemToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eintrag löschen?</AlertDialogTitle>
            <AlertDialogDescription>
              Möchten Sie den Eintrag für <strong>{itemToDelete?.ticker}</strong> wirklich löschen? 
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
