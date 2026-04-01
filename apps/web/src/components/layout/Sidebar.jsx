
import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, PieChart, List, LineChart, Settings, LogOut } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext.jsx';
import { cn } from '@/lib/utils.js';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
  { icon: PieChart, label: 'Portfolio', path: '/portfolio' },
  { icon: List, label: 'Watchlist', path: '/watchlist' },
  { icon: LineChart, label: 'Analyse', path: '/analyse' },
];

export default function Sidebar() {
  const { logout } = useAuth();

  return (
    <aside className="w-64 border-r bg-card hidden md:flex flex-col h-full min-h-[calc(100vh-4rem)]">
      <div className="flex-1 py-6 px-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium",
                isActive 
                  ? "bg-primary/10 text-primary" 
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </div>
      
      <div className="p-4 border-t space-y-1">
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
        >
          <LogOut className="h-4 w-4" />
          Abmelden
        </button>
      </div>
    </aside>
  );
}
