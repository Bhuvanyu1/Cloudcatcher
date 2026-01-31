import { useEffect, useState } from "react";
import { 
  Search, 
  RefreshCw, 
  Filter,
  Server,
  Globe,
  Lock,
  ChevronDown,
  ChevronUp,
  X
} from "lucide-react";
import { 
  SiAmazonwebservices, 
  SiMicrosoftazure, 
  SiGooglecloud, 
  SiDigitalocean 
} from "react-icons/si";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getInstances, getCloudAccounts, syncAllAccounts } from "@/lib/api";
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

const stateColors = {
  running: "bg-primary text-primary-foreground",
  stopped: "bg-destructive text-destructive-foreground",
  pending: "bg-[#FFFF00] text-black",
  terminated: "bg-muted text-muted-foreground"
};

export default function Inventory() {
  const [instances, setInstances] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  
  // Filters
  const [filters, setFilters] = useState({
    provider: "",
    cloud_account_id: "",
    state: "",
    name: "",
    region: ""
  });

  const fetchData = async () => {
    try {
      const [instancesRes, accountsRes] = await Promise.all([
        getInstances(Object.fromEntries(
          Object.entries(filters).filter(([_, v]) => v)
        )),
        getCloudAccounts()
      ]);
      setInstances(instancesRes.data);
      setAccounts(accountsRes.data);
    } catch (error) {
      toast.error("Failed to load inventory");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await syncAllAccounts();
      toast.success(`Found ${response.data.instances_found} instances`);
      fetchData();
    } catch (error) {
      toast.error("Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const clearFilters = () => {
    setFilters({
      provider: "",
      cloud_account_id: "",
      state: "",
      name: "",
      region: ""
    });
  };

  const activeFilterCount = Object.values(filters).filter(v => v).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]" data-testid="inventory-loading">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="inventory-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading font-black text-4xl tracking-tighter uppercase">
            INVENTORY
          </h1>
          <p className="text-muted-foreground text-sm uppercase tracking-wider mt-1">
            {instances.length} instances across {accounts.length} accounts
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            data-testid="toggle-filters-btn"
            className="border-2 border-border font-bold uppercase"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
            {activeFilterCount > 0 && (
              <Badge className="ml-2 bg-primary text-primary-foreground">
                {activeFilterCount}
              </Badge>
            )}
          </Button>
          <Button
            onClick={handleSync}
            disabled={syncing}
            data-testid="inventory-sync-btn"
            className="bg-primary text-primary-foreground border-2 border-primary hover:border-white hard-shadow font-bold uppercase tracking-wider active-press"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "SYNCING..." : "SYNC NOW"}
          </Button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333] animate-slide-in">
          <CardHeader className="border-b-2 border-border p-4 bg-muted/20">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading font-bold text-sm uppercase">
                FILTER INSTANCES
              </CardTitle>
              {activeFilterCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="text-xs uppercase"
                  data-testid="clear-filters-btn"
                >
                  <X className="w-3 h-3 mr-1" /> Clear All
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Search by Name */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Search Name
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    value={filters.name}
                    onChange={(e) => setFilters(f => ({ ...f, name: e.target.value }))}
                    placeholder="Instance name..."
                    className="pl-10 border-2 border-border bg-input"
                    data-testid="filter-name"
                  />
                </div>
              </div>

              {/* Provider Filter */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Provider
                </label>
                <Select 
                  value={filters.provider} 
                  onValueChange={(v) => setFilters(f => ({ ...f, provider: v }))}
                >
                  <SelectTrigger className="border-2 border-border bg-input" data-testid="filter-provider">
                    <SelectValue placeholder="All Providers" />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-2 border-border">
                    <SelectItem value="">All Providers</SelectItem>
                    <SelectItem value="aws">AWS</SelectItem>
                    <SelectItem value="azure">Azure</SelectItem>
                    <SelectItem value="gcp">GCP</SelectItem>
                    <SelectItem value="do">DigitalOcean</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Account Filter */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Account
                </label>
                <Select 
                  value={filters.cloud_account_id} 
                  onValueChange={(v) => setFilters(f => ({ ...f, cloud_account_id: v }))}
                >
                  <SelectTrigger className="border-2 border-border bg-input" data-testid="filter-account">
                    <SelectValue placeholder="All Accounts" />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-2 border-border">
                    <SelectItem value="">All Accounts</SelectItem>
                    {accounts.map(acc => (
                      <SelectItem key={acc.id} value={acc.id}>
                        {acc.account_name || acc.id.slice(0, 8)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* State Filter */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  State
                </label>
                <Select 
                  value={filters.state} 
                  onValueChange={(v) => setFilters(f => ({ ...f, state: v }))}
                >
                  <SelectTrigger className="border-2 border-border bg-input" data-testid="filter-state">
                    <SelectValue placeholder="All States" />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-2 border-border">
                    <SelectItem value="">All States</SelectItem>
                    <SelectItem value="running">Running</SelectItem>
                    <SelectItem value="stopped">Stopped</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="terminated">Terminated</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Region Filter */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Region
                </label>
                <Input
                  value={filters.region}
                  onChange={(e) => setFilters(f => ({ ...f, region: e.target.value }))}
                  placeholder="e.g., us-east-1"
                  className="border-2 border-border bg-input"
                  data-testid="filter-region"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Instances Table */}
      <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333]">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-b-2 border-border bg-muted/30 hover:bg-muted/30">
                <TableHead className="font-bold uppercase text-xs tracking-wider">Provider</TableHead>
                <TableHead className="font-bold uppercase text-xs tracking-wider">Name</TableHead>
                <TableHead className="font-bold uppercase text-xs tracking-wider">Instance ID</TableHead>
                <TableHead className="font-bold uppercase text-xs tracking-wider">Type</TableHead>
                <TableHead className="font-bold uppercase text-xs tracking-wider">Region</TableHead>
                <TableHead className="font-bold uppercase text-xs tracking-wider">State</TableHead>
                <TableHead className="font-bold uppercase text-xs tracking-wider">Public IP</TableHead>
                <TableHead className="font-bold uppercase text-xs tracking-wider">Private IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {instances.length > 0 ? (
                instances.map((instance) => {
                  const ProviderIcon = providerIcons[instance.provider];
                  const providerColor = providerColors[instance.provider];
                  
                  return (
                    <TableRow 
                      key={instance.id}
                      className="border-b border-border/50 hover:bg-muted/20 cursor-pointer table-row-hover"
                      onClick={() => setSelectedInstance(instance)}
                      data-testid={`instance-row-${instance.instance_id}`}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {ProviderIcon && (
                            <ProviderIcon className="w-4 h-4" style={{ color: providerColor }} />
                          )}
                          <span className="uppercase text-xs font-bold">{instance.provider}</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm font-medium">
                        {instance.name || "-"}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {instance.instance_id}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {instance.instance_type_or_size || "-"}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {instance.region_or_zone || "-"}
                      </TableCell>
                      <TableCell>
                        <Badge className={`uppercase text-[10px] font-bold border-0 ${stateColors[instance.state] || "bg-muted"}`}>
                          {instance.state || "unknown"}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {instance.public_ip ? (
                          <div className="flex items-center gap-1">
                            <Globe className="w-3 h-3 text-secondary" />
                            {instance.public_ip}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {instance.private_ip ? (
                          <div className="flex items-center gap-1">
                            <Lock className="w-3 h-3 text-muted-foreground" />
                            {instance.private_ip}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={8} className="h-48 text-center">
                    <Server className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                    <p className="font-bold uppercase text-muted-foreground">No instances found</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {activeFilterCount > 0 
                        ? "Try adjusting your filters" 
                        : "Add cloud accounts and sync to see instances"}
                    </p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      {/* Instance Detail Dialog */}
      <Dialog open={!!selectedInstance} onOpenChange={() => setSelectedInstance(null)}>
        <DialogContent className="bg-card border-2 border-border shadow-[8px_8px_0px_0px_#333] max-w-2xl">
          <DialogHeader className="border-b-2 border-border pb-4">
            <DialogTitle className="font-heading font-bold text-xl uppercase flex items-center gap-2">
              <Server className="w-5 h-5 text-primary" />
              Instance Details
            </DialogTitle>
          </DialogHeader>
          
          {selectedInstance && (
            <div className="space-y-4 py-4" data-testid="instance-detail-modal">
              {/* Header Info */}
              <div className="flex items-center gap-4 p-4 bg-muted/20 border-2 border-border">
                {providerIcons[selectedInstance.provider] && (
                  <div className="p-3 border-2" style={{ borderColor: providerColors[selectedInstance.provider] }}>
                    {(() => {
                      const Icon = providerIcons[selectedInstance.provider];
                      return <Icon className="w-8 h-8" style={{ color: providerColors[selectedInstance.provider] }} />;
                    })()}
                  </div>
                )}
                <div>
                  <h3 className="font-bold text-lg">{selectedInstance.name || "Unnamed Instance"}</h3>
                  <p className="font-mono text-sm text-muted-foreground">{selectedInstance.instance_id}</p>
                </div>
                <Badge className={`ml-auto uppercase text-xs font-bold border-0 ${stateColors[selectedInstance.state] || "bg-muted"}`}>
                  {selectedInstance.state}
                </Badge>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Provider</p>
                  <p className="font-mono mt-1">{selectedInstance.provider?.toUpperCase()}</p>
                </div>
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Instance Type</p>
                  <p className="font-mono mt-1">{selectedInstance.instance_type_or_size || "-"}</p>
                </div>
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Region / Zone</p>
                  <p className="font-mono mt-1">{selectedInstance.region_or_zone || "-"}</p>
                </div>
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">State</p>
                  <p className="font-mono mt-1">{selectedInstance.state || "-"}</p>
                </div>
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Public IP</p>
                  <p className="font-mono mt-1">{selectedInstance.public_ip || "None"}</p>
                </div>
                <div className="p-3 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground">Private IP</p>
                  <p className="font-mono mt-1">{selectedInstance.private_ip || "None"}</p>
                </div>
              </div>

              {/* Tags */}
              {selectedInstance.tags && Object.keys(selectedInstance.tags).length > 0 && (
                <div className="p-4 bg-muted/10 border border-border">
                  <p className="text-xs font-bold uppercase text-muted-foreground mb-3">Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(selectedInstance.tags).map(([key, value]) => (
                      <Badge 
                        key={key} 
                        variant="outline"
                        className="font-mono text-xs border-border"
                      >
                        {key}: {value}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Timestamps */}
              <div className="flex gap-4 text-xs text-muted-foreground">
                <span>First seen: {new Date(selectedInstance.first_seen_at).toLocaleString()}</span>
                <span>Last seen: {new Date(selectedInstance.last_seen_at).toLocaleString()}</span>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
