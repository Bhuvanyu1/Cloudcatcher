import { useEffect, useState } from "react";
import { 
  AlertTriangle, 
  DollarSign, 
  Shield, 
  RefreshCw,
  CheckCircle,
  XCircle,
  ChevronRight,
  Cloud
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { 
  getRecommendations, 
  updateRecommendationStatus, 
  runRecommendations,
  getCloudAccounts 
} from "@/lib/api";
import { toast } from "sonner";

const providerConfig = {
  aws: { color: "#FF9900", label: "AWS" },
  azure: { color: "#0078D4", label: "Azure" },
  gcp: { color: "#4285F4", label: "GCP" },
  do: { color: "#0080FF", label: "DO" }
};

const severityConfig = {
  high: { color: "bg-destructive text-destructive-foreground", icon: AlertTriangle, priority: 1 },
  medium: { color: "bg-[#FF9900] text-black", icon: AlertTriangle, priority: 2 },
  low: { color: "bg-secondary text-secondary-foreground", icon: AlertTriangle, priority: 3 }
};

const categoryConfig = {
  finops: { icon: DollarSign, color: "text-[#FF9900]", label: "FINOPS" },
  secops: { icon: Shield, color: "text-destructive", label: "SECOPS" }
};

export default function Recommendations() {
  const [recommendations, setRecommendations] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedRec, setSelectedRec] = useState(null);
  const [activeTab, setActiveTab] = useState("all");
  
  // Filters
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("open");

  const fetchData = async () => {
    try {
      const params = {
        status: statusFilter !== "all" ? statusFilter : undefined,
        severity: severityFilter !== "all" ? severityFilter : undefined,
        category: activeTab !== "all" ? activeTab : undefined
      };
      
      const [recsRes, accountsRes] = await Promise.all([
        getRecommendations(params),
        getCloudAccounts()
      ]);
      
      // Sort by severity priority
      const sorted = recsRes.data.sort((a, b) => {
        const priorityA = severityConfig[a.severity]?.priority || 99;
        const priorityB = severityConfig[b.severity]?.priority || 99;
        return priorityA - priorityB;
      });
      
      setRecommendations(sorted);
      setAccounts(accountsRes.data);
    } catch (error) {
      toast.error("Failed to load recommendations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab, severityFilter, statusFilter]);

  const handleRunRecommendations = async () => {
    setGenerating(true);
    try {
      const response = await runRecommendations();
      toast.success(`Generated ${response.data.recommendations_generated} recommendations`);
      fetchData();
    } catch (error) {
      toast.error("Failed to generate recommendations");
    } finally {
      setGenerating(false);
    }
  };

  const handleStatusUpdate = async (id, newStatus) => {
    try {
      await updateRecommendationStatus(id, newStatus);
      toast.success(`Recommendation ${newStatus}`);
      setSelectedRec(null);
      fetchData();
    } catch (error) {
      toast.error("Failed to update recommendation");
    }
  };

  const getAccountName = (accountId) => {
    const account = accounts.find(a => a.id === accountId);
    return account?.account_name || accountId?.slice(0, 8) || "Unknown";
  };

  const stats = {
    total: recommendations.length,
    high: recommendations.filter(r => r.severity === "high").length,
    medium: recommendations.filter(r => r.severity === "medium").length,
    low: recommendations.filter(r => r.severity === "low").length,
    finops: recommendations.filter(r => r.category === "finops").length,
    secops: recommendations.filter(r => r.category === "secops").length
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]" data-testid="recommendations-loading">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="recommendations-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading font-black text-4xl tracking-tighter uppercase">
            RECOMMENDATIONS
          </h1>
          <p className="text-muted-foreground text-sm uppercase tracking-wider mt-1">
            FinOps & SecOps insights for your infrastructure
          </p>
        </div>
        <Button
          onClick={handleRunRecommendations}
          disabled={generating}
          data-testid="generate-recs-btn"
          className="bg-primary text-primary-foreground border-2 border-primary hover:border-white hard-shadow font-bold uppercase tracking-wider active-press"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${generating ? "animate-spin" : ""}`} />
          {generating ? "ANALYZING..." : "RUN ANALYSIS"}
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <Card className="bg-card border-2 border-border shadow-[2px_2px_0px_0px_#333]">
          <CardContent className="p-4 text-center">
            <p className="text-xs font-bold uppercase text-muted-foreground">Total</p>
            <p className="text-2xl font-black mt-1" data-testid="stat-total">{stats.total}</p>
          </CardContent>
        </Card>
        <Card className="bg-card border-2 border-destructive shadow-[2px_2px_0px_0px_#FF3333]">
          <CardContent className="p-4 text-center">
            <p className="text-xs font-bold uppercase text-destructive">High</p>
            <p className="text-2xl font-black mt-1 text-destructive" data-testid="stat-high">{stats.high}</p>
          </CardContent>
        </Card>
        <Card className="bg-card border-2 border-[#FF9900] shadow-[2px_2px_0px_0px_#FF9900]">
          <CardContent className="p-4 text-center">
            <p className="text-xs font-bold uppercase text-[#FF9900]">Medium</p>
            <p className="text-2xl font-black mt-1 text-[#FF9900]" data-testid="stat-medium">{stats.medium}</p>
          </CardContent>
        </Card>
        <Card className="bg-card border-2 border-secondary shadow-[2px_2px_0px_0px_#00FFFF]">
          <CardContent className="p-4 text-center">
            <p className="text-xs font-bold uppercase text-secondary">Low</p>
            <p className="text-2xl font-black mt-1 text-secondary" data-testid="stat-low">{stats.low}</p>
          </CardContent>
        </Card>
        <Card className="bg-card border-2 border-border shadow-[2px_2px_0px_0px_#333]">
          <CardContent className="p-4 text-center">
            <div className="flex items-center justify-center gap-1">
              <DollarSign className="w-4 h-4 text-[#FF9900]" />
              <p className="text-xs font-bold uppercase text-muted-foreground">FinOps</p>
            </div>
            <p className="text-2xl font-black mt-1" data-testid="stat-finops">{stats.finops}</p>
          </CardContent>
        </Card>
        <Card className="bg-card border-2 border-border shadow-[2px_2px_0px_0px_#333]">
          <CardContent className="p-4 text-center">
            <div className="flex items-center justify-center gap-1">
              <Shield className="w-4 h-4 text-destructive" />
              <p className="text-xs font-bold uppercase text-muted-foreground">SecOps</p>
            </div>
            <p className="text-2xl font-black mt-1" data-testid="stat-secops">{stats.secops}</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs & Filters */}
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full md:w-auto">
          <TabsList className="bg-muted border-2 border-border p-1 h-auto">
            <TabsTrigger 
              value="all"
              data-testid="tab-all"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold uppercase text-xs px-4 py-2"
            >
              All
            </TabsTrigger>
            <TabsTrigger 
              value="finops"
              data-testid="tab-finops"
              className="data-[state=active]:bg-[#FF9900] data-[state=active]:text-black font-bold uppercase text-xs px-4 py-2"
            >
              <DollarSign className="w-3 h-3 mr-1" />
              FinOps
            </TabsTrigger>
            <TabsTrigger 
              value="secops"
              data-testid="tab-secops"
              className="data-[state=active]:bg-destructive data-[state=active]:text-destructive-foreground font-bold uppercase text-xs px-4 py-2"
            >
              <Shield className="w-3 h-3 mr-1" />
              SecOps
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="flex gap-2">
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="w-[140px] border-2 border-border bg-input" data-testid="filter-severity">
              <SelectValue placeholder="All Severity" />
            </SelectTrigger>
            <SelectContent className="bg-card border-2 border-border">
              <SelectItem value="all">All Severity</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px] border-2 border-border bg-input" data-testid="filter-status">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent className="bg-card border-2 border-border">
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="dismissed">Dismissed</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Recommendations List */}
      <div className="space-y-3">
        {recommendations.length > 0 ? (
          recommendations.map((rec) => {
            const CategoryIcon = categoryConfig[rec.category]?.icon || AlertTriangle;
            const ProviderIcon = providerIcons[rec.provider];
            const severityCfg = severityConfig[rec.severity] || severityConfig.low;
            
            return (
              <Card 
                key={rec.id}
                className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333] hover:border-primary/50 transition-colors cursor-pointer card-hover"
                onClick={() => setSelectedRec(rec)}
                data-testid={`rec-card-${rec.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    {/* Severity Indicator */}
                    <div className={`p-2 border-2 ${rec.severity === 'high' ? 'border-destructive' : rec.severity === 'medium' ? 'border-[#FF9900]' : 'border-secondary'}`}>
                      <CategoryIcon className={`w-5 h-5 ${categoryConfig[rec.category]?.color}`} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <Badge className={`text-[10px] uppercase font-bold border-0 ${severityCfg.color}`}>
                          {rec.severity}
                        </Badge>
                        <Badge variant="outline" className="text-[10px] uppercase font-bold">
                          {rec.category}
                        </Badge>
                        <Badge variant="outline" className="text-[10px] uppercase font-bold font-mono">
                          {rec.rule_id}
                        </Badge>
                        {rec.status !== "open" && (
                          <Badge 
                            variant="outline" 
                            className={`text-[10px] uppercase font-bold ${rec.status === 'resolved' ? 'text-primary border-primary' : 'text-muted-foreground'}`}
                          >
                            {rec.status}
                          </Badge>
                        )}
                      </div>

                      <h3 className="font-bold text-sm mb-1">{rec.title}</h3>
                      <p className="text-xs text-muted-foreground line-clamp-2">{rec.description}</p>

                      {/* Meta */}
                      <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                        {ProviderIcon && (
                          <div className="flex items-center gap-1">
                            <ProviderIcon className="w-3 h-3" style={{ color: providerColors[rec.provider] }} />
                            <span className="uppercase">{rec.provider}</span>
                          </div>
                        )}
                        <span>Account: {getAccountName(rec.cloud_account_id)}</span>
                        {rec.resource_id && (
                          <span className="font-mono">{rec.resource_id}</span>
                        )}
                      </div>
                    </div>

                    {/* Arrow */}
                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            );
          })
        ) : (
          <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333]">
            <CardContent className="p-12 text-center">
              <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
              <h3 className="font-heading font-bold text-xl uppercase mb-2">
                No Recommendations Found
              </h3>
              <p className="text-muted-foreground mb-6">
                {statusFilter === "open" 
                  ? "All clear! No open recommendations." 
                  : "No recommendations match your filters."}
              </p>
              <Button
                onClick={handleRunRecommendations}
                disabled={generating}
                data-testid="empty-generate-btn"
                className="bg-primary text-primary-foreground border-2 border-primary font-bold uppercase"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${generating ? "animate-spin" : ""}`} />
                Run Analysis
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Recommendation Detail Dialog */}
      <Dialog open={!!selectedRec} onOpenChange={() => setSelectedRec(null)}>
        <DialogContent className="bg-card border-2 border-border shadow-[8px_8px_0px_0px_#333] max-w-2xl">
          <DialogHeader className="border-b-2 border-border pb-4">
            <DialogTitle className="font-heading font-bold text-xl uppercase flex items-center gap-2">
              {selectedRec?.category === "finops" ? (
                <DollarSign className="w-5 h-5 text-[#FF9900]" />
              ) : (
                <Shield className="w-5 h-5 text-destructive" />
              )}
              Recommendation Details
            </DialogTitle>
          </DialogHeader>
          
          {selectedRec && (
            <div className="space-y-4 py-4" data-testid="rec-detail-modal">
              {/* Badges */}
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className={`text-xs uppercase font-bold border-0 ${severityConfig[selectedRec.severity]?.color}`}>
                  {selectedRec.severity} severity
                </Badge>
                <Badge variant="outline" className="text-xs uppercase font-bold">
                  {selectedRec.category}
                </Badge>
                <Badge variant="outline" className="text-xs uppercase font-bold font-mono">
                  {selectedRec.rule_id}
                </Badge>
              </div>

              {/* Title & Description */}
              <div>
                <h3 className="font-bold text-lg mb-2">{selectedRec.title}</h3>
                <p className="text-sm text-muted-foreground">{selectedRec.description}</p>
              </div>

              {/* Evidence */}
              {selectedRec.evidence && Object.keys(selectedRec.evidence).length > 0 && (
                <div className="p-4 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground mb-3">Evidence</p>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(selectedRec.evidence).map(([key, value]) => (
                      <div key={key}>
                        <p className="text-xs text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</p>
                        <p className="font-mono text-sm">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Resource Info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Provider</p>
                  <p className="font-mono mt-1 uppercase">{selectedRec.provider}</p>
                </div>
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Account</p>
                  <p className="font-mono mt-1">{getAccountName(selectedRec.cloud_account_id)}</p>
                </div>
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Resource Type</p>
                  <p className="font-mono mt-1">{selectedRec.resource_type}</p>
                </div>
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Resource ID</p>
                  <p className="font-mono mt-1 text-xs">{selectedRec.resource_id || "-"}</p>
                </div>
              </div>

              {/* Status */}
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Created: {new Date(selectedRec.created_at).toLocaleString()}</span>
                <span>•</span>
                <span>Status: {selectedRec.status}</span>
              </div>
            </div>
          )}

          <DialogFooter className="border-t-2 border-border pt-4 gap-2">
            {selectedRec?.status === "open" && (
              <>
                <Button
                  variant="outline"
                  onClick={() => handleStatusUpdate(selectedRec.id, "dismissed")}
                  data-testid="dismiss-rec-btn"
                  className="border-2 border-muted-foreground"
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  Dismiss
                </Button>
                <Button
                  onClick={() => handleStatusUpdate(selectedRec.id, "resolved")}
                  data-testid="resolve-rec-btn"
                  className="bg-primary text-primary-foreground border-2 border-primary"
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Mark Resolved
                </Button>
              </>
            )}
            {selectedRec?.status !== "open" && (
              <Button
                variant="outline"
                onClick={() => handleStatusUpdate(selectedRec.id, "open")}
                data-testid="reopen-rec-btn"
                className="border-2 border-primary text-primary"
              >
                Reopen
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
