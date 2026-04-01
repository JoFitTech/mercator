
import React, { useState, useEffect } from 'react';
import pb from '@/lib/pocketbaseClient.js';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';

const PositionForm = ({ open, onOpenChange, position, onSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    ticker: '',
    isin: '',
    name: '',
    assetType: 'Aktie',
    category: '',
    region: '',
    country: '',
    sector: '',
    currency: 'EUR',
    shares: '',
    buyPrice: '',
    buyDate: new Date().toISOString().split('T')[0],
    currentPriceManual: '',
    isCore: false,
    isSatellite: false,
    thesis: '',
    notes: ''
  });

  useEffect(() => {
    if (position) {
      setFormData({
        ticker: position.ticker || '',
        isin: position.isin || '',
        name: position.name || '',
        assetType: position.assetType || 'Aktie',
        category: position.category || '',
        region: position.region || '',
        country: position.country || '',
        sector: position.sector || '',
        currency: position.currency || 'EUR',
        shares: position.shares || '',
        buyPrice: position.buyPrice || '',
        buyDate: position.buyDate ? position.buyDate.split(' ')[0] : new Date().toISOString().split('T')[0],
        currentPriceManual: position.currentPriceManual || '',
        isCore: position.isCore || false,
        isSatellite: position.isSatellite || false,
        thesis: position.thesis || '',
        notes: position.notes || ''
      });
    } else {
      setFormData({
        ticker: '',
        isin: '',
        name: '',
        assetType: 'Aktie',
        category: '',
        region: '',
        country: '',
        sector: '',
        currency: 'EUR',
        shares: '',
        buyPrice: '',
        buyDate: new Date().toISOString().split('T')[0],
        currentPriceManual: '',
        isCore: false,
        isSatellite: false,
        thesis: '',
        notes: ''
      });
    }
  }, [position, open]);

  const handleChange = (field, value) => {
    setFormData(prev => {
      const newData = { ...prev, [field]: value };
      if (field === 'isCore' && value) newData.isSatellite = false;
      if (field === 'isSatellite' && value) newData.isCore = false;
      return newData;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const dataToSubmit = {
        ...formData,
        userId: pb.authStore.model.id,
        shares: Number(formData.shares),
        buyPrice: Number(formData.buyPrice),
        currentPriceManual: formData.currentPriceManual ? Number(formData.currentPriceManual) : null,
        currentPriceUpdatedAt: formData.currentPriceManual ? new Date().toISOString() : null,
        buyDate: new Date(formData.buyDate).toISOString()
      };

      if (position?.id) {
        await pb.collection('portfolio_positions').update(position.id, dataToSubmit, { $autoCancel: false });
        toast.success('Position erfolgreich aktualisiert');
      } else {
        await pb.collection('portfolio_positions').create(dataToSubmit, { $autoCancel: false });
        toast.success('Position erfolgreich erstellt');
      }
      
      onSuccess();
      onOpenChange(false);
    } catch (error) {
      console.error('Error saving position:', error);
      toast.error('Fehler beim Speichern der Position');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{position ? 'Position bearbeiten' : 'Neue Position'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ticker">Ticker *</Label>
              <Input id="ticker" value={formData.ticker} onChange={e => handleChange('ticker', e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="isin">ISIN</Label>
              <Input id="isin" value={formData.isin} onChange={e => handleChange('isin', e.target.value)} />
            </div>
            <div className="space-y-2 col-span-2">
              <Label htmlFor="name">Name *</Label>
              <Input id="name" value={formData.name} onChange={e => handleChange('name', e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="assetType">Asset-Typ *</Label>
              <Select value={formData.assetType} onValueChange={v => handleChange('assetType', v)}>
                <SelectTrigger><SelectValue placeholder="Wählen..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Aktie">Aktie</SelectItem>
                  <SelectItem value="ETF">ETF</SelectItem>
                  <SelectItem value="Anleihe">Anleihe</SelectItem>
                  <SelectItem value="Fonds">Fonds</SelectItem>
                  <SelectItem value="Kryptowährung">Kryptowährung</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="category">Kategorie</Label>
              <Input id="category" value={formData.category} onChange={e => handleChange('category', e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="region">Region</Label>
              <Select value={formData.region} onValueChange={v => handleChange('region', v)}>
                <SelectTrigger><SelectValue placeholder="Wählen..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Europa">Europa</SelectItem>
                  <SelectItem value="Nordamerika">Nordamerika</SelectItem>
                  <SelectItem value="Asien">Asien</SelectItem>
                  <SelectItem value="Pazifik">Pazifik</SelectItem>
                  <SelectItem value="Emerging Markets">Emerging Markets</SelectItem>
                  <SelectItem value="Global">Global</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="country">Land *</Label>
              <Input id="country" value={formData.country} onChange={e => handleChange('country', e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sector">Branche</Label>
              <Input id="sector" value={formData.sector} onChange={e => handleChange('sector', e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="currency">Währung *</Label>
              <Select value={formData.currency} onValueChange={v => handleChange('currency', v)}>
                <SelectTrigger><SelectValue placeholder="Wählen..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="EUR">EUR</SelectItem>
                  <SelectItem value="USD">USD</SelectItem>
                  <SelectItem value="GBP">GBP</SelectItem>
                  <SelectItem value="JPY">JPY</SelectItem>
                  <SelectItem value="CHF">CHF</SelectItem>
                  <SelectItem value="KRW">KRW</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="shares">Stückzahl *</Label>
              <Input id="shares" type="number" step="any" min="0.00001" value={formData.shares} onChange={e => handleChange('shares', e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="buyPrice">Kaufkurs *</Label>
              <Input id="buyPrice" type="number" step="any" min="0.00001" value={formData.buyPrice} onChange={e => handleChange('buyPrice', e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="buyDate">Kaufdatum *</Label>
              <Input id="buyDate" type="date" value={formData.buyDate} onChange={e => handleChange('buyDate', e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="currentPriceManual">Aktueller Kurs (manuell)</Label>
              <Input id="currentPriceManual" type="number" step="any" min="0" value={formData.currentPriceManual} onChange={e => handleChange('currentPriceManual', e.target.value)} />
            </div>
          </div>

          <div className="flex gap-6 py-2">
            <div className="flex items-center space-x-2">
              <Checkbox id="isCore" checked={formData.isCore} onCheckedChange={v => handleChange('isCore', v)} />
              <Label htmlFor="isCore">Core-Position</Label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox id="isSatellite" checked={formData.isSatellite} onCheckedChange={v => handleChange('isSatellite', v)} />
              <Label htmlFor="isSatellite">Satellite-Position</Label>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="thesis">These</Label>
            <Textarea id="thesis" value={formData.thesis} onChange={e => handleChange('thesis', e.target.value)} rows={3} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="notes">Notizen</Label>
            <Textarea id="notes" value={formData.notes} onChange={e => handleChange('notes', e.target.value)} rows={2} />
          </div>

          <DialogFooter className="pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Abbrechen</Button>
            <Button type="submit" disabled={isLoading}>{isLoading ? 'Speichern...' : 'Speichern'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default PositionForm;
