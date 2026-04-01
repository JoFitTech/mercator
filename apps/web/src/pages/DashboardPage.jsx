
import React, { useState, useEffect } from 'react';
import pb from '@/lib/pocketbaseClient.js';
import MainLayout from '@/components/layout/MainLayout.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const COLORS = ['hsl(var(--primary))', 'hsl(var(--chart-2, 160 60% 45%))', 'hsl(var(--muted-foreground))'];

const DashboardPage = () => {
  const [positions, setPositions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const records = await pb.collection('portfolio_positions').getFullList({
          sort: '-created',
          $autoCancel: false
        });
        setPositions(records);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const getEURValue = (val, currency) => {
    const rates = { USD: 0.92, CHF: 1.03, GBP: 1.17, JPY: 0.0061, KRW: 0.00069, EUR: 1 };
    return val * (rates[currency] || 1);
  };

  let totalCurrentEUR = 0;
  const countryMap = {};
  
  positions.forEach(p => {
    const current = p.shares * (p.currentPriceManual || p.buyPrice);
    const valEUR = getEURValue(current, p.currency);
    totalCurrentEUR += valEUR;
    countryMap[p.country] = (countryMap[p.country] || 0) + valEUR;
  });

  const formatEUR = (val) => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(val);

  const strategyData = [
    { name: 'Core', value: positions.filter(p => p.isCore).reduce((sum, p) => sum + getEURValue(p.shares * (p.currentPriceManual || p.buyPrice), p.currency), 0) },
    { name: 'Satellite', value: positions.filter(p => p.isSatellite).reduce((sum, p) => sum + getEURValue(p.shares * (p.currentPriceManual || p.buyPrice), p.currency), 0) }
  ].filter(d => d.value > 0);

  const topCountries = Object.entries(countryMap)
    .map(([name, value]) => ({ name, value, percent: totalCurrentEUR > 0 ? (value / totalCurrentEUR) * 100 : 0 }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 3);

  const recentPositions = [...positions].sort((a, b) => new Date(b.buyDate) - new Date(a.buyDate)).slice(0, 3);

  return (
    <MainLayout title="Dashboard">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Willkommen bei Mercator. Hier finden Sie eine Übersicht Ihrer Investments.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Portfolio Positionen</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{isLoading ? '-' : positions.length}</div>
              <p className="text-xs text-muted-foreground">Aktive Investments</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Portfolio Wert</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{isLoading ? '-' : formatEUR(totalCurrentEUR)}</div>
              <p className="text-xs text-muted-foreground">Aktueller Gesamtwert</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Watchlist</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
              <p className="text-xs text-muted-foreground">Beobachtete Werte</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Analysen</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
              <p className="text-xs text-muted-foreground">Abgeschlossene Analysen</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Core vs Satellite</CardTitle>
            </CardHeader>
            <CardContent className="h-[200px]">
              {isLoading ? (
                <div className="h-full flex items-center justify-center text-muted-foreground">Laden...</div>
              ) : strategyData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={strategyData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={2} dataKey="value">
                      {strategyData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatEUR(value)} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">Keine Daten</div>
              )}
            </CardContent>
          </Card>

          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Top 3 Länder</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {topCountries.map(country => (
                  <div key={country.name} className="flex items-center justify-between">
                    <span className="font-medium">{country.name}</span>
                    <span className="text-muted-foreground">{country.percent.toFixed(1)}%</span>
                  </div>
                ))}
                {topCountries.length === 0 && !isLoading && (
                  <div className="text-muted-foreground text-center py-4">Keine Daten</div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Letzte Positionen</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentPositions.map(pos => (
                  <div key={pos.id} className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{pos.ticker}</div>
                      <div className="text-xs text-muted-foreground">{pos.name}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{new Intl.NumberFormat('de-DE', { style: 'currency', currency: pos.currency }).format(pos.buyPrice)}</div>
                    </div>
                  </div>
                ))}
                {recentPositions.length === 0 && !isLoading && (
                  <div className="text-muted-foreground text-center py-4">Keine Daten</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
};

export default DashboardPage;
