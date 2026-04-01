
import React, { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, Edit2, Trash2, Eye, ArrowUpDown } from 'lucide-react';

const PortfolioPositionsTab = ({ positions, onEdit, onDelete, onView }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [assetFilter, setAssetFilter] = useState('all');
  const [strategyFilter, setStrategyFilter] = useState('all');
  const [sortConfig, setSortConfig] = useState({ key: 'name', direction: 'asc' });

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const filteredPositions = positions.filter(p => {
    const matchesSearch = p.ticker.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          p.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesAsset = assetFilter === 'all' || p.assetType === assetFilter;
    const matchesStrategy = strategyFilter === 'all' || 
                            (strategyFilter === 'core' && p.isCore) || 
                            (strategyFilter === 'satellite' && p.isSatellite);
    return matchesSearch && matchesAsset && matchesStrategy;
  });

  const sortedPositions = [...filteredPositions].sort((a, b) => {
    let valA = a[sortConfig.key];
    let valB = b[sortConfig.key];

    if (sortConfig.key === 'value') {
      valA = a.shares * (a.currentPriceManual || a.buyPrice);
      valB = b.shares * (b.currentPriceManual || b.buyPrice);
    }

    if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  const formatCurrency = (val, currency) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: currency || 'EUR' }).format(val);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Suchen nach Ticker oder Name..."
            className="pl-8"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <Select value={assetFilter} onValueChange={setAssetFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Asset-Typ" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle Typen</SelectItem>
            <SelectItem value="Aktie">Aktie</SelectItem>
            <SelectItem value="ETF">ETF</SelectItem>
            <SelectItem value="Anleihe">Anleihe</SelectItem>
          </SelectContent>
        </Select>
        <Select value={strategyFilter} onValueChange={setStrategyFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Strategie" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle Strategien</SelectItem>
            <SelectItem value="core">Core</SelectItem>
            <SelectItem value="satellite">Satellite</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border border-border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="cursor-pointer hover:bg-muted/50" onClick={() => handleSort('ticker')}>
                Ticker <ArrowUpDown className="inline h-3 w-3 ml-1" />
              </TableHead>
              <TableHead className="cursor-pointer hover:bg-muted/50" onClick={() => handleSort('name')}>
                Name <ArrowUpDown className="inline h-3 w-3 ml-1" />
              </TableHead>
              <TableHead>Typ</TableHead>
              <TableHead>Strategie</TableHead>
              <TableHead className="text-right">Stückzahl</TableHead>
              <TableHead className="text-right">Kaufkurs</TableHead>
              <TableHead className="text-right">Akt. Kurs</TableHead>
              <TableHead className="text-right cursor-pointer hover:bg-muted/50" onClick={() => handleSort('value')}>
                Wert <ArrowUpDown className="inline h-3 w-3 ml-1" />
              </TableHead>
              <TableHead className="text-right">Aktionen</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedPositions.map((pos) => {
              const currentPrice = pos.currentPriceManual || pos.buyPrice;
              const value = pos.shares * currentPrice;
              
              return (
                <TableRow key={pos.id}>
                  <TableCell className="font-medium">{pos.ticker}</TableCell>
                  <TableCell>{pos.name}</TableCell>
                  <TableCell>{pos.assetType}</TableCell>
                  <TableCell>
                    {pos.isCore && <Badge variant="default" className="text-[10px]">Core</Badge>}
                    {pos.isSatellite && <Badge variant="secondary" className="text-[10px]">Satellite</Badge>}
                  </TableCell>
                  <TableCell className="text-right">{pos.shares}</TableCell>
                  <TableCell className="text-right">{formatCurrency(pos.buyPrice, pos.currency)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(currentPrice, pos.currency)}</TableCell>
                  <TableCell className="text-right font-medium">{formatCurrency(value, pos.currency)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onView(pos)}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(pos)}>
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive" onClick={() => onDelete(pos)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
            {sortedPositions.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                  Keine Positionen gefunden.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default PortfolioPositionsTab;
