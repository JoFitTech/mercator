
import React, { useState, useEffect } from 'react';
import pb from '@/lib/pocketbaseClient.js';
import MainLayout from '@/components/layout/MainLayout.jsx';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import PortfolioOverviewTab from '@/components/portfolio/PortfolioOverviewTab.jsx';
import PortfolioPositionsTab from '@/components/portfolio/PortfolioPositionsTab.jsx';
import PortfolioAllocationTab from '@/components/portfolio/PortfolioAllocationTab.jsx';
import PortfolioBIPComparisonTab from '@/components/portfolio/PortfolioBIPComparisonTab.jsx';
import PositionForm from '@/components/portfolio/PositionForm.jsx';
import PositionDetailModal from '@/components/portfolio/PositionDetailModal.jsx';

const PortfolioPage = () => {
  const [positions, setPositions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Modal states
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState(null);

  const fetchPositions = async () => {
    setIsLoading(true);
    try {
      const records = await pb.collection('portfolio_positions').getFullList({
        sort: '-created',
        $autoCancel: false
      });
      setPositions(records);
    } catch (error) {
      console.error('Error fetching positions:', error);
      toast.error('Fehler beim Laden der Portfolio-Daten');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
  }, []);

  const handleCreate = () => {
    setSelectedPosition(null);
    setFormOpen(true);
  };

  const handleEdit = (position) => {
    setSelectedPosition(position);
    setDetailOpen(false);
    setFormOpen(true);
  };

  const handleView = (position) => {
    setSelectedPosition(position);
    setDetailOpen(true);
  };

  const handleDelete = async (position) => {
    if (window.confirm(`Möchten Sie die Position ${position.ticker} wirklich löschen?`)) {
      try {
        await pb.collection('portfolio_positions').delete(position.id, { $autoCancel: false });
        toast.success('Position gelöscht');
        setDetailOpen(false);
        fetchPositions();
      } catch (error) {
        console.error('Error deleting position:', error);
        toast.error('Fehler beim Löschen der Position');
      }
    }
  };

  return (
    <MainLayout title="Portfolio">
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
            <p className="text-muted-foreground mt-1">
              Verwalten und analysieren Sie Ihre aktiven Investment-Positionen.
            </p>
          </div>
          <Button onClick={handleCreate}>
            <Plus className="mr-2 h-4 w-4" /> Neue Position
          </Button>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center py-24">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-8">
              <TabsTrigger value="overview">Übersicht</TabsTrigger>
              <TabsTrigger value="positions">Positionen</TabsTrigger>
              <TabsTrigger value="allocation">Allokation</TabsTrigger>
              <TabsTrigger value="bip">BIP-Vergleich</TabsTrigger>
            </TabsList>
            
            <TabsContent value="overview" className="mt-0">
              <PortfolioOverviewTab positions={positions} />
            </TabsContent>
            
            <TabsContent value="positions" className="mt-0">
              <PortfolioPositionsTab 
                positions={positions} 
                onEdit={handleEdit} 
                onDelete={handleDelete} 
                onView={handleView} 
              />
            </TabsContent>
            
            <TabsContent value="allocation" className="mt-0">
              <PortfolioAllocationTab positions={positions} />
            </TabsContent>
            
            <TabsContent value="bip" className="mt-0">
              <PortfolioBIPComparisonTab positions={positions} />
            </TabsContent>
          </Tabs>
        )}
      </div>

      <PositionForm 
        open={formOpen} 
        onOpenChange={setFormOpen} 
        position={selectedPosition} 
        onSuccess={fetchPositions} 
      />
      
      <PositionDetailModal 
        open={detailOpen} 
        onOpenChange={setDetailOpen} 
        position={selectedPosition} 
        onEdit={handleEdit} 
        onDelete={handleDelete} 
      />
    </MainLayout>
  );
};

export default PortfolioPage;
