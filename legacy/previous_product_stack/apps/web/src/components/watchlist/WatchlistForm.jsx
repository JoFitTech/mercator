
import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import pb from '@/lib/pocketbaseClient';
import { toast } from 'sonner';

const ITEM_TYPES = ['Aktie', 'ETF', 'Pennystock', 'Insider', 'Sonstiges'];
const STATUS_OPTIONS = ['Beobachten', 'Watchlist', 'Kaufkandidat', 'Archiviert'];

export default function WatchlistForm({ isOpen, onClose, item, onSuccess }) {
  const [formData, setFormData] = useState({
    ticker: '',
    name: '',
    itemType: '',
    status: 'Beobachten',
    notes: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (item) {
      setFormData({
        ticker: item.ticker || '',
        name: item.name || '',
        itemType: item.itemType || '',
        status: item.status || 'Beobachten',
        notes: item.notes || ''
      });
    } else {
      setFormData({
        ticker: '',
        name: '',
        itemType: '',
        status: 'Beobachten',
        notes: ''
      });
    }
    setErrors({});
  }, [item, isOpen]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.ticker.trim()) newErrors.ticker = 'Ticker ist erforderlich';
    if (!formData.name.trim()) newErrors.name = 'Name ist erforderlich';
    if (!formData.itemType) newErrors.itemType = 'Typ ist erforderlich';
    if (!formData.status) newErrors.status = 'Status ist erforderlich';
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const dataToSave = {
        ...formData,
        userId: pb.authStore.model.id
      };

      if (item?.id) {
        await pb.collection('watchlist_items').update(item.id, dataToSave, { $autoCancel: false });
        toast.success('Eintrag aktualisiert');
      } else {
        await pb.collection('watchlist_items').create(dataToSave, { $autoCancel: false });
        toast.success('Eintrag erstellt');
      }
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error saving watchlist item:', error);
      toast.error('Fehler beim Speichern des Eintrags');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{item ? 'Eintrag bearbeiten' : 'Neuer Eintrag'}</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ticker">Ticker *</Label>
              <Input 
                id="ticker" 
                value={formData.ticker} 
                onChange={(e) => handleChange('ticker', e.target.value)}
                placeholder="z.B. AAPL"
                className={errors.ticker ? 'border-destructive' : ''}
              />
              {errors.ticker && <p className="text-xs text-destructive">{errors.ticker}</p>}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input 
                id="name" 
                value={formData.name} 
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="z.B. Apple Inc."
                className={errors.name ? 'border-destructive' : ''}
              />
              {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="itemType">Typ *</Label>
              <Select value={formData.itemType} onValueChange={(val) => handleChange('itemType', val)}>
                <SelectTrigger className={errors.itemType ? 'border-destructive' : ''}>
                  <SelectValue placeholder="Typ wählen" />
                </SelectTrigger>
                <SelectContent>
                  {ITEM_TYPES.map(type => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.itemType && <p className="text-xs text-destructive">{errors.itemType}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">Status *</Label>
              <Select value={formData.status} onValueChange={(val) => handleChange('status', val)}>
                <SelectTrigger className={errors.status ? 'border-destructive' : ''}>
                  <SelectValue placeholder="Status wählen" />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map(status => (
                    <SelectItem key={status} value={status}>{status}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.status && <p className="text-xs text-destructive">{errors.status}</p>}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes">Notizen</Label>
            <Textarea 
              id="notes" 
              value={formData.notes} 
              onChange={(e) => handleChange('notes', e.target.value)}
              placeholder="Optionale Notizen zum Unternehmen..."
              className="min-h-[100px]"
            />
          </div>

          <DialogFooter className="pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Abbrechen
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Speichern...' : 'Speichern'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
