
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis } from 'recharts';

const COLORS = ['hsl(var(--primary))', 'hsl(var(--chart-2, 160 60% 45%))', 'hsl(var(--chart-3, 30 80% 55%))', 'hsl(var(--chart-4, 280 65% 60%))', 'hsl(var(--chart-5, 340 75% 55%))', 'hsl(var(--muted-foreground))'];

const PortfolioAllocationTab = ({ positions }) => {
  const getEURValue = (val, currency) => {
    const rates = { USD: 0.92, CHF: 1.03, GBP: 1.17, JPY: 0.0061, KRW: 0.00069, EUR: 1 };
    return val * (rates[currency] || 1);
  };

  const aggregateData = (key) => {
    const map = {};
    let total = 0;
    positions.forEach(p => {
      const val = getEURValue(p.shares * (p.currentPriceManual || p.buyPrice), p.currency);
      const groupKey = p[key] || 'Unbekannt';
      map[groupKey] = (map[groupKey] || 0) + val;
      total += val;
    });
    
    return Object.entries(map)
      .map(([name, value]) => ({ name, value, percent: total > 0 ? (value / total) * 100 : 0 }))
      .sort((a, b) => b.value - a.value);
  };

  const regionData = aggregateData('region');
  const sectorData = aggregateData('sector');
  const currencyData = aggregateData('currency');
  const countryData = aggregateData('country').slice(0, 10);

  const formatPercent = (val) => `${val.toFixed(1)}%`;
  const formatEUR = (val) => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(val);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-popover border border-border p-3 rounded-lg shadow-lg">
          <p className="font-medium">{payload[0].name}</p>
          <p className="text-sm text-muted-foreground">{formatEUR(payload[0].value)}</p>
          <p className="text-sm font-bold">{formatPercent(payload[0].payload.percent)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Größte Region</CardTitle></CardHeader>
          <CardContent>
            <div className="text-xl font-bold truncate">{regionData[0]?.name || '-'}</div>
            <div className="text-sm text-primary">{regionData[0] ? formatPercent(regionData[0].percent) : '0%'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Größtes Land</CardTitle></CardHeader>
          <CardContent>
            <div className="text-xl font-bold truncate">{countryData[0]?.name || '-'}</div>
            <div className="text-sm text-primary">{countryData[0] ? formatPercent(countryData[0].percent) : '0%'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Größte Branche</CardTitle></CardHeader>
          <CardContent>
            <div className="text-xl font-bold truncate">{sectorData[0]?.name || '-'}</div>
            <div className="text-sm text-primary">{sectorData[0] ? formatPercent(sectorData[0].percent) : '0%'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Größte Währung</CardTitle></CardHeader>
          <CardContent>
            <div className="text-xl font-bold truncate">{currencyData[0]?.name || '-'}</div>
            <div className="text-sm text-primary">{currencyData[0] ? formatPercent(currencyData[0].percent) : '0%'}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Regionen</CardTitle></CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={regionData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} dataKey="value">
                  {regionData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Branchen</CardTitle></CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={sectorData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} dataKey="value">
                  {sectorData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader><CardTitle>Top 10 Länder</CardTitle></CardHeader>
          <CardContent className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={countryData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <XAxis dataKey="name" axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip content={<CustomTooltip />} cursor={{fill: 'transparent'}} />
                <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} maxBarSize={60}>
                  {countryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default PortfolioAllocationTab;
