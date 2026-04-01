
import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const PositionDetailModal = ({ open, onOpenChange, position, onEdit, onDelete }) => {
  if (!position) return null;

  const investedValue = position.shares * position.buyPrice;
  const currentPrice = position.currentPriceManual || position.buyPrice;
  const currentValue = position.shares * currentPrice;
  const absoluteDiff = currentValue - investedValue;
  const percentDiff = investedValue > 0 ? (absoluteDiff / investedValue) * 100 : 0;

  const formatCurrency = (val, currency) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: currency || 'EUR' }).format(val);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <div className="flex items-center justify-between pr-6">
            <DialogTitle className="text-xl">{position.name} ({position.ticker})</DialogTitle>
            <div className="flex gap-2">
              {position.isCore && <Badge variant="default">Core</Badge>}
              {position.isSatellite && <Badge variant="secondary">Satellite</Badge>}
              <Badge variant="outline">{position.assetType}</Badge>
            </div>
          </div>
        </DialogHeader>
        
        <div className="grid grid-cols-2 gap-6 py-4">
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Stammdaten</h4>
              <div className="grid grid-cols-2 gap-y-1 text-sm">
                <span className="text-muted-foreground">ISIN:</span>
                <span>{position.isin || '-'}</span>
                <span className="text-muted-foreground">Land:</span>
                <span>{position.country}</span>
                <span className="text-muted-foreground">Region:</span>
                <span>{position.region || '-'}</span>
                <span className="text-muted-foreground">Branche:</span>
                <span>{position.sector || '-'}</span>
                <span className="text-muted-foreground">Währung:</span>
                <span>{position.currency}</span>
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Kaufdaten</h4>
              <div className="grid grid-cols-2 gap-y-1 text-sm">
                <span className="text-muted-foreground">Stückzahl:</span>
                <span>{position.shares}</span>
                <span className="text-muted-foreground">Kaufkurs:</span>
                <span>{formatCurrency(position.buyPrice, position.currency)}</span>
                <span className="text-muted-foreground">Kaufdatum:</span>
                <span>{new Date(position.buyDate).toLocaleDateString('de-DE')}</span>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-muted/50 p-4 rounded-lg space-y-3">
              <h4 className="text-sm font-medium text-muted-foreground">Performance</h4>
              <div className="flex justify-between items-end">
                <span className="text-sm">Investiert:</span>
                <span className="font-medium">{formatCurrency(investedValue, position.currency)}</span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-sm">Aktueller Wert:</span>
                <span className="font-medium">{formatCurrency(currentValue, position.currency)}</span>
              </div>
              <div className="pt-2 border-t border-border flex justify-between items-end">
                <span className="text-sm">Rendite:</span>
                <div className={`text-right ${absoluteDiff >= 0 ? 'text-emerald-500' : 'text-destructive'}`}>
                  <div className="font-bold">{absoluteDiff > 0 ? '+' : ''}{formatCurrency(absoluteDiff, position.currency)}</div>
                  <div className="text-xs">{absoluteDiff > 0 ? '+' : ''}{percentDiff.toFixed(2)}%</div>
                </div>
              </div>
            </div>
          </div>

          <div className="col-span-2 space-y-4">
            {position.thesis && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">These</h4>
                <p className="text-sm bg-muted/30 p-3 rounded-md">{position.thesis}</p>
              </div>
            )}
            {position.notes && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">Notizen</h4>
                <p className="text-sm bg-muted/30 p-3 rounded-md">{position.notes}</p>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="destructive" onClick={() => onDelete(position)}>Löschen</Button>
          <Button variant="outline" onClick={() => onEdit(position)}>Bearbeiten</Button>
          <Button onClick={() => onOpenChange(false)}>Schließen</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default PositionDetailModal;
