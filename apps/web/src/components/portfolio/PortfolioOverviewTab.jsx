
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

const COLORS = ['hsl(var(--primary))', 'hsl(var(--chart-2, 160 60% 45%))', 'hsl(var(--chart-3, 30 80% 55%))', 'hsl(var(--chart-4, 280 65% 60%))', 'hsl(var(--chart-5, 340 75% 55%))'];

const PortfolioOverviewTab = ({ positions }) => {
  // Calculations
  const totalPositions = positions.length;
  const coreCount = positions.filter(p => p.isCore).length;
  const satelliteCount = positions.filter(p => p.isSatellite).length;

  let totalInvestedEUR = 0;
  let totalCurrentEUR = 0;

  // Simplified currency conversion for demo purposes (1:1 if not EUR)
  // In a real app, you'd fetch live exchange rates
  const getEURValue = (val, currency) => {
    const rates = { USD: 0.92, CHF: 1.03, GBP: 1.17, JPY: 0.0061, KRW: 0.00069, EUR: 1 };
    return val * (rates[currency] || 1);
  };

  positions.forEach(p => {
    const invested = p.shares * p.buyPrice;
    const current = p.shares * (p.currentPriceManual || p.buyPrice);
    totalInvestedEUR += getEURValue(invested, p.currency);
    totalCurrentEUR += getEURValue(current, p.currency);
  });

  const absoluteDiff = totalCurrentEUR - totalInvestedEUR;
  const percentDiff = totalInvestedEUR > 0 ? (absoluteDiff / totalInvestedEUR) * 100 : 0;

  // Top 5 Countries
  const countryMap = {};
  positions.forEach(p => {
    const current = p.shares * (p.currentPriceManual || p.buyPrice);
    const valEUR = getEURValue(current, p.currency);
    countryMap[p.country] = (countryMap[p.country] || 0) + valEUR;
  });
  const countryData = Object.entries(countryMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5);

  // Core vs Satellite
  const strategyData = [
    { name: 'Core', value: positions.filter(p => p.isCore).reduce((sum, p) => sum + getEURValue(p.shares * (p.currentPriceManual || p.buyPrice), p.currency), 0) },
    { name: 'Satellite', value: positions.filter(p => p.isSatellite).reduce((sum, p) => sum + getEURValue(p.shares * (p.currentPriceManual || p.buyPrice), p.currency), 0) },
    { name: 'Unkategorisiert', value: positions.filter(p => !p.isCore && !p.isSatellite).reduce((sum, p) => sum + getEURValue(p.shares * (p.currentPriceManual || p.buyPrice), p.currency), 0) }
  ].filter(d => d.value > 0);

  // Last 5 positions
  const recentPositions = [...positions].sort((a, b) => new Date(b.buyDate) - new Date(a.buyDate)).slice(0, 5);

  const formatEUR = (val) => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(val);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Gesamtwert</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatEUR(totalCurrentEUR)}</div>
            <p className="text-xs text-muted-foreground">Investiert: {formatEUR(totalInvestedEUR)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${absoluteDiff >= 0 ? 'text-emerald-500' : 'text-destructive'}`}>
              {absoluteDiff > 0 ? '+' : ''}{formatEUR(absoluteDiff)}
            </div>
            <p className="text-xs text-muted-foreground">{absoluteDiff > 0 ? '+' : ''}{percentDiff.toFixed(2)}% Gesamtrendite</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Positionen</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalPositions}</div>
            <p className="text-xs text-muted-foreground">Aktive Investments</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Strategie</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{coreCount} <span className="text-lg font-normal text-muted-foreground">Core</span></div>
            <p className="text-xs text-muted-foreground">{satelliteCount} Satellite Positionen</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top 5 Länder</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={countryData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} fontSize={12} />
                <Tooltip formatter={(value) => formatEUR(value)} cursor={{fill: 'transparent'}} />
                <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} barSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Core vs Satellite</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={strategyData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} dataKey="value">
                  {strategyData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatEUR(value)} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-4 mt-4">
              {strategyData.map((entry, index) => (
                <div key={entry.name} className="flex items-center gap-2 text-sm">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <span>{entry.name}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Zuletzt hinzugefügt</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ticker</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Kaufdatum</TableHead>
                <TableHead className="text-right">Kaufkurs</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentPositions.map((pos) => (
                <TableRow key={pos.id}>
                  <TableCell className="font-medium">{pos.ticker}</TableCell>
                  <TableCell>{pos.name}</TableCell>
                  <TableCell>{new Date(pos.buyDate).toLocaleDateString('de-DE')}</TableCell>
                  <TableCell className="text-right">
                    {new Intl.NumberFormat('de-DE', { style: 'currency', currency: pos.currency }).format(pos.buyPrice)}
                  </TableCell>
                </TableRow>
              ))}
              {recentPositions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-6">Keine Positionen vorhanden</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default PortfolioOverviewTab;
