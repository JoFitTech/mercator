
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';

const REFERENCE_DATA = {
  'Nordamerika': 60,
  'Europa': 20,
  'Asien': 15,
  'Pazifik': 5,
  'Emerging Markets': 0,
  'Global': 0
};

const PortfolioBIPComparisonTab = ({ positions }) => {
  const getEURValue = (val, currency) => {
    const rates = { USD: 0.92, CHF: 1.03, GBP: 1.17, JPY: 0.0061, KRW: 0.00069, EUR: 1 };
    return val * (rates[currency] || 1);
  };

  const map = {};
  let total = 0;
  positions.forEach(p => {
    const val = getEURValue(p.shares * (p.currentPriceManual || p.buyPrice), p.currency);
    const region = p.region || 'Unbekannt';
    map[region] = (map[region] || 0) + val;
    total += val;
  });

  const comparisonData = Object.keys(REFERENCE_DATA).map(region => {
    const portfolioWeight = total > 0 ? ((map[region] || 0) / total) * 100 : 0;
    const referenceWeight = REFERENCE_DATA[region];
    const diff = portfolioWeight - referenceWeight;
    
    return {
      region,
      portfolio: Number(portfolioWeight.toFixed(1)),
      reference: referenceWeight,
      diff: Number(diff.toFixed(1))
    };
  }).sort((a, b) => b.reference - a.reference);

  return (
    <div className="space-y-6">
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader>
          <CardTitle>Referenzansicht (Demo-Daten)</CardTitle>
          <CardDescription>
            Vergleich der Portfolio-Gewichtung nach Regionen mit einem statischen Referenzindex (z.B. MSCI World).
          </CardDescription>
        </CardHeader>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Abweichungsanalyse</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Region</TableHead>
                  <TableHead className="text-right">Portfolio</TableHead>
                  <TableHead className="text-right">Referenz</TableHead>
                  <TableHead className="text-right">Abweichung</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {comparisonData.map((row) => (
                  <TableRow key={row.region}>
                    <TableCell className="font-medium">{row.region}</TableCell>
                    <TableCell className="text-right">{row.portfolio}%</TableCell>
                    <TableCell className="text-right text-muted-foreground">{row.reference}%</TableCell>
                    <TableCell className={`text-right font-medium ${row.diff > 0 ? 'text-emerald-500' : row.diff < 0 ? 'text-destructive' : ''}`}>
                      {row.diff > 0 ? '+' : ''}{row.diff}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Gewichtungsvergleich</CardTitle>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <XAxis dataKey="region" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} tickFormatter={(val) => `${val}%`} />
                <Tooltip 
                  cursor={{fill: 'hsl(var(--muted))'}}
                  contentStyle={{ backgroundColor: 'hsl(var(--popover))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                  formatter={(value) => [`${value}%`]}
                />
                <Legend />
                <Bar dataKey="portfolio" name="Portfolio" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                <Bar dataKey="reference" name="Referenz" fill="hsl(var(--muted-foreground))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default PortfolioBIPComparisonTab;
