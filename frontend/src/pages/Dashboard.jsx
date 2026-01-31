import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { 
  Server, 
  Cloud, 
  AlertTriangle, 
  DollarSign, 
  Shield, 
  RefreshCw,
  ArrowRight,
  Activity
} from "lucide-react";
import { 
  SiAmazonwebservices, 
  SiMicrosoft, 
  SiGooglecloud, 
  SiDigitalocean 
} from "react-icons/si";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getDashboardStats, getRecommendations, syncAllAccounts } from "@/lib/api";
import { toast } from "sonner";

const providerIcons = {
  aws: SiAmazonwebservices,
  azure: SiMicrosoftazure,
  gcp: SiGooglecloud,
  do: SiDigitalocean
};

const providerColors = {
  aws: "#FF9900",
  azure: "#0078D4",
  gcp: "#4285F4",
  do: "#0080FF"
};

const providerNames = {
  aws: "AWS",
  azure: "Azure",
  gcp: "GCP",
  do: "DigitalOcean"
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchData = async () => {
    try {
      const [statsRes, recsRes] = await Promise.all([
        getDashboardStats(),
        getRecommendations({ status: "open", limit: 5 })
      ]);
      setStats(statsRes.data);
      setRecommendations(recsRes.data);
    } catch (error) {
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await syncAllAccounts();
      if (response.data.success) {
        toast.success(`Synced ${response.data.accounts_synced} accounts`);
        fetchData();
      }
    } catch (error) {
      toast.error("Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]" data-testid="dashboard-loading">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading font-black text-4xl tracking-tighter uppercase">
            DASHBOARD
          </h1>
          <p className="text-muted-foreground text-sm uppercase tracking-wider mt-1">
            Multi-cloud inventory overview
          </p>
        </div>
        <Button
          onClick={handleSync}
          disabled={syncing}
          data-testid="dashboard-sync-btn"
          className="bg-primary text-primary-foreground border-2 border-primary hover:border-white hard-shadow font-bold uppercase tracking-wider active-press"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
          {syncing ? "SYNCING..." : "SYNC NOW"}
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Instances */}
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333] card-hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  TOTAL INSTANCES
                </p>
                <p className="text-4xl font-black mt-2" data-testid="stat-total-instances">
                  {stats?.total_instances || 0}
                </p>
              </div>
              <div className="p-3 bg-primary/10 border-2 border-primary">
                <Server className="w-6 h-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cloud Accounts */}
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333] card-hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  CLOUD ACCOUNTS
                </p>
                <p className="text-4xl font-black mt-2" data-testid="stat-total-accounts">
                  {stats?.total_accounts || 0}
                </p>
              </div>
              <div className="p-3 bg-secondary/10 border-2 border-secondary">
                <Cloud className="w-6 h-6 text-secondary" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* FinOps Alerts */}
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333] card-hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  FINOPS ALERTS
                </p>
                <p className="text-4xl font-black mt-2" data-testid="stat-finops-alerts">
                  {stats?.finops_recommendations || 0}
                </p>
              </div>
              <div className="p-3 bg-[#FF9900]/10 border-2 border-[#FF9900]">
                <DollarSign className="w-6 h-6 text-[#FF9900]" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* SecOps Alerts */}
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333] card-hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  SECOPS ALERTS
                </p>
                <p className="text-4xl font-black mt-2" data-testid="stat-secops-alerts">
                  {stats?.secops_recommendations || 0}
                </p>
              </div>
              <div className="p-3 bg-destructive/10 border-2 border-destructive">
                <Shield className="w-6 h-6 text-destructive" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Provider Breakdown & Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Instances by Provider */}
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333]">
          <CardHeader className="border-b-2 border-border bg-muted/20 p-4">
            <CardTitle className="font-heading font-bold text-lg uppercase tracking-tight flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              INSTANCES BY PROVIDER
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {stats?.instances_by_provider && Object.keys(stats.instances_by_provider).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(stats.instances_by_provider).map(([provider, count]) => {
                  const Icon = providerIcons[provider];
                  const color = providerColors[provider];
                  const total = stats.total_instances || 1;
                  const percentage = Math.round((count / total) * 100);
                  
                  return (
                    <div key={provider} className="space-y-2" data-testid={`provider-${provider}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {Icon && <Icon className="w-5 h-5" style={{ color }} />}
                          <span className="font-bold uppercase">{providerNames[provider] || provider}</span>
                        </div>
                        <span className="font-mono font-bold">{count}</span>
                      </div>
                      <div className="h-2 bg-muted border border-border">
                        <div 
                          className="h-full transition-all duration-500"
                          style={{ width: `${percentage}%`, backgroundColor: color }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Server className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="font-bold uppercase">No instances synced yet</p>
                <p className="text-sm mt-1">Add cloud accounts and sync to see data</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Recommendations */}
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333]">
          <CardHeader className="border-b-2 border-border bg-muted/20 p-4">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading font-bold text-lg uppercase tracking-tight flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-destructive" />
                RECENT ALERTS
              </CardTitle>
              <Link to="/recommendations">
                <Button variant="ghost" size="sm" className="text-xs uppercase" data-testid="view-all-recs-btn">
                  View All <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="p-4">
            {recommendations.length > 0 ? (
              <div className="space-y-3">
                {recommendations.slice(0, 5).map((rec) => (
                  <div 
                    key={rec.id}
                    className="p-3 border-2 border-border bg-muted/10 hover:border-primary/50 transition-colors"
                    data-testid={`rec-${rec.id}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge 
                            className={`text-[10px] uppercase font-bold border-0 ${
                              rec.severity === "high" ? "bg-destructive text-destructive-foreground" :
                              rec.severity === "medium" ? "bg-[#FF9900] text-black" :
                              "bg-secondary text-secondary-foreground"
                            }`}
                          >
                            {rec.severity}
                          </Badge>
                          <Badge 
                            variant="outline"
                            className="text-[10px] uppercase font-bold"
                          >
                            {rec.category}
                          </Badge>
                        </div>
                        <p className="font-bold text-sm truncate">{rec.title}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="font-bold uppercase">No open alerts</p>
                <p className="text-sm mt-1">All clear!</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Instance States */}
      {stats?.instances_by_state && Object.keys(stats.instances_by_state).length > 0 && (
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333]">
          <CardHeader className="border-b-2 border-border bg-muted/20 p-4">
            <CardTitle className="font-heading font-bold text-lg uppercase tracking-tight">
              INSTANCE STATES
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="flex flex-wrap gap-4">
              {Object.entries(stats.instances_by_state).map(([state, count]) => {
                const stateColors = {
                  running: "bg-primary text-primary-foreground border-primary",
                  stopped: "bg-destructive text-destructive-foreground border-destructive",
                  pending: "bg-[#FFFF00] text-black border-[#FFFF00]",
                  terminated: "bg-muted text-muted-foreground border-muted"
                };
                
                return (
                  <div 
                    key={state}
                    className={`px-4 py-2 border-2 font-mono font-bold ${stateColors[state] || "bg-muted border-border"}`}
                    data-testid={`state-${state}`}
                  >
                    <span className="uppercase">{state}</span>
                    <span className="ml-2 text-lg">{count}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Last Sync Info */}
      {stats?.last_sync && (
        <div className="text-center text-sm text-muted-foreground">
          <span className="uppercase tracking-wider">Last sync: </span>
          <span className="font-mono">{new Date(stats.last_sync).toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
