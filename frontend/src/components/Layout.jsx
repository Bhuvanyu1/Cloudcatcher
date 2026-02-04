import { Outlet, NavLink, useLocation } from "react-router-dom";
import { 
  LayoutDashboard, 
  Cloud, 
  Server, 
  AlertTriangle, 
  RefreshCw,
  Menu,
  X,
  LogOut,
  User,
  Settings
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { syncAllAccounts } from "@/lib/api";
import { toast } from "sonner";
import { useState } from "react";
import { getUser, logout } from "@/components/ProtectedRoute";

// Provider icons as colored text badges
const ProviderIcon = ({ provider, className = "" }) => {
  const config = {
    aws: { color: "#FF9900", label: "AWS" },
    azure: { color: "#0078D4", label: "AZ" },
    gcp: { color: "#4285F4", label: "GCP" },
    do: { color: "#0080FF", label: "DO" }
  };
  const p = config[provider] || config.aws;
  return (
    <span 
      className={`font-bold text-xs ${className}`} 
      style={{ color: p.color }}
    >
      {p.label}
    </span>
  );
};

const navItems = [
  { path: "/", icon: LayoutDashboard, label: "DASHBOARD" },
  { path: "/accounts", icon: Cloud, label: "ACCOUNTS" },
  { path: "/inventory", icon: Server, label: "INVENTORY" },
  { path: "/recommendations", icon: AlertTriangle, label: "RECOMMENDATIONS" },
];

export default function Layout() {
  const location = useLocation();
  const [syncing, setSyncing] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const user = getUser();

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await syncAllAccounts();
      if (response.data.success) {
        toast.success(`Synced ${response.data.accounts_synced} accounts, found ${response.data.instances_found} instances`);
      } else {
        toast.warning("Sync completed with errors", {
          description: response.data.errors.join(", ")
        });
      }
    } catch (error) {
      toast.error("Sync failed", {
        description: error.response?.data?.detail || error.message
      });
    } finally {
      setSyncing(false);
    }
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="flex min-h-screen bg-background" data-testid="app-layout">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex flex-col w-64 border-r-2 border-border bg-card">
        {/* Logo */}
        <div className="p-6 border-b-2 border-border">
          <h1 className="font-heading font-black text-2xl tracking-tighter uppercase text-foreground">
            CLOUD<span className="text-primary">WATCHER</span>
          </h1>
          <p className="text-xs text-muted-foreground mt-1 uppercase tracking-widest">
            Multi-Cloud Ops
          </p>
        </div>

        {/* Provider Icons */}
        <div className="flex justify-around p-4 border-b-2 border-border bg-muted/20">
          <ProviderIcon provider="aws" />
          <ProviderIcon provider="azure" />
          <ProviderIcon provider="gcp" />
          <ProviderIcon provider="do" />
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
                className={`
                  flex items-center gap-3 px-4 py-3 text-sm font-bold uppercase tracking-wider
                  border-2 transition-all active-press
                  ${isActive 
                    ? "bg-primary text-primary-foreground border-primary hard-shadow-sm" 
                    : "bg-transparent text-foreground border-border hover:border-primary hover:bg-muted/50"
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Sync Button */}
        <div className="p-4 border-t-2 border-border space-y-3">
          <Button
            onClick={handleSync}
            disabled={syncing}
            data-testid="sync-all-btn"
            className="w-full bg-secondary text-secondary-foreground border-2 border-secondary hover:border-white font-bold uppercase tracking-wider active-press"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "SYNCING..." : "SYNC ALL"}
          </Button>
          
          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="outline" 
                className="w-full border-2 border-border justify-start gap-2"
                data-testid="user-menu-btn"
              >
                <User className="w-4 h-4" />
                <span className="truncate text-xs">{user?.name || "User"}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 bg-card border-2 border-border">
              <div className="px-2 py-1.5">
                <p className="text-sm font-bold">{user?.name}</p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
                <p className="text-xs text-primary uppercase mt-1">{user?.role}</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="cursor-pointer" onClick={handleLogout}>
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-card border-b-2 border-border">
        <div className="flex items-center justify-between p-4">
          <h1 className="font-heading font-black text-xl tracking-tighter uppercase">
            CLOUD<span className="text-primary">WATCHER</span>
          </h1>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            data-testid="mobile-menu-btn"
            className="border-2 border-border"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </Button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="border-t-2 border-border bg-card p-4 space-y-2">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  data-testid={`mobile-nav-${item.label.toLowerCase()}`}
                  className={`
                    flex items-center gap-3 px-4 py-3 text-sm font-bold uppercase tracking-wider
                    border-2 transition-all
                    ${isActive 
                      ? "bg-primary text-primary-foreground border-primary" 
                      : "bg-transparent text-foreground border-border"
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </NavLink>
              );
            })}
            <Button
              onClick={() => { handleSync(); setMobileMenuOpen(false); }}
              disabled={syncing}
              data-testid="mobile-sync-btn"
              className="w-full bg-secondary text-secondary-foreground border-2 border-secondary font-bold uppercase"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "SYNCING..." : "SYNC ALL"}
            </Button>
          </div>
        )}
      </div>

      {/* Main Content */}
      <main className="flex-1 md:p-6 p-4 pt-20 md:pt-6 overflow-auto custom-scrollbar">
        <div className="max-w-[1600px] mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
