import { useEffect, useState } from "react";
import { 
  Plus, 
  RefreshCw, 
  Trash2, 
  Edit2, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader2
} from "lucide-react";
import { 
  SiAmazonwebservices, 
  SiMicrosoft, 
  SiGooglecloud, 
  SiDigitalocean 
} from "react-icons/si";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { 
  getCloudAccounts, 
  createCloudAccount, 
  deleteCloudAccount, 
  syncAccount 
} from "@/lib/api";
import { toast } from "sonner";

const providers = [
  { value: "aws", label: "AWS", icon: SiAmazonwebservices, color: "#FF9900" },
  { value: "azure", label: "Azure", icon: SiMicrosoft, color: "#0078D4" },
  { value: "gcp", label: "GCP", icon: SiGooglecloud, color: "#4285F4" },
  { value: "do", label: "DigitalOcean", icon: SiDigitalocean, color: "#0080FF" },
];

const statusConfig = {
  connected: { icon: CheckCircle, color: "text-primary", bg: "bg-primary/10", label: "CONNECTED" },
  error: { icon: XCircle, color: "text-destructive", bg: "bg-destructive/10", label: "ERROR" },
  disabled: { icon: AlertCircle, color: "text-muted-foreground", bg: "bg-muted", label: "DISABLED" },
  syncing: { icon: Loader2, color: "text-secondary", bg: "bg-secondary/10", label: "SYNCING" },
};

const credentialFields = {
  aws: [
    { key: "access_key_id", label: "Access Key ID", type: "text" },
    { key: "secret_access_key", label: "Secret Access Key", type: "password" },
    { key: "region", label: "Default Region", type: "text", placeholder: "us-east-1" },
  ],
  azure: [
    { key: "tenant_id", label: "Tenant ID", type: "text" },
    { key: "client_id", label: "Client ID", type: "text" },
    { key: "client_secret", label: "Client Secret", type: "password" },
    { key: "subscription_id", label: "Subscription ID", type: "text" },
  ],
  gcp: [
    { key: "project_id", label: "Project ID", type: "text" },
    { key: "service_account_json", label: "Service Account JSON", type: "textarea" },
  ],
  do: [
    { key: "token", label: "Personal Access Token", type: "password" },
  ],
};

export default function CloudAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [accountToDelete, setAccountToDelete] = useState(null);
  const [syncingId, setSyncingId] = useState(null);
  
  // Form state
  const [selectedProvider, setSelectedProvider] = useState("");
  const [accountName, setAccountName] = useState("");
  const [credentials, setCredentials] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const fetchAccounts = async () => {
    try {
      const response = await getCloudAccounts();
      setAccounts(response.data);
    } catch (error) {
      toast.error("Failed to load cloud accounts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleProviderChange = (provider) => {
    setSelectedProvider(provider);
    setCredentials({});
  };

  const handleCredentialChange = (key, value) => {
    setCredentials(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (!selectedProvider) {
      toast.error("Please select a provider");
      return;
    }

    setSubmitting(true);
    try {
      await createCloudAccount({
        provider: selectedProvider,
        account_name: accountName || undefined,
        credentials: credentials
      });
      toast.success("Cloud account added successfully");
      setDialogOpen(false);
      resetForm();
      fetchAccounts();
    } catch (error) {
      toast.error("Failed to add cloud account", {
        description: error.response?.data?.detail || error.message
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!accountToDelete) return;
    
    try {
      await deleteCloudAccount(accountToDelete.id);
      toast.success("Cloud account deleted");
      setDeleteDialogOpen(false);
      setAccountToDelete(null);
      fetchAccounts();
    } catch (error) {
      toast.error("Failed to delete cloud account");
    }
  };

  const handleSync = async (accountId) => {
    setSyncingId(accountId);
    try {
      const response = await syncAccount(accountId);
      toast.success(`Found ${response.data.instances_found} instances`);
      fetchAccounts();
    } catch (error) {
      toast.error("Sync failed");
    } finally {
      setSyncingId(null);
    }
  };

  const resetForm = () => {
    setSelectedProvider("");
    setAccountName("");
    setCredentials({});
  };

  const getProviderInfo = (providerValue) => {
    return providers.find(p => p.value === providerValue) || providers[0];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]" data-testid="accounts-loading">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="cloud-accounts-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading font-black text-4xl tracking-tighter uppercase">
            CLOUD ACCOUNTS
          </h1>
          <p className="text-muted-foreground text-sm uppercase tracking-wider mt-1">
            Manage your cloud provider connections
          </p>
        </div>
        <Button
          onClick={() => setDialogOpen(true)}
          data-testid="add-account-btn"
          className="bg-primary text-primary-foreground border-2 border-primary hover:border-white hard-shadow font-bold uppercase tracking-wider active-press"
        >
          <Plus className="w-4 h-4 mr-2" />
          ADD ACCOUNT
        </Button>
      </div>

      {/* Accounts Grid */}
      {accounts.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((account) => {
            const providerInfo = getProviderInfo(account.provider);
            const status = statusConfig[account.status] || statusConfig.connected;
            const StatusIcon = status.icon;
            const ProviderIcon = providerInfo.icon;

            return (
              <Card 
                key={account.id}
                className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333] card-hover"
                data-testid={`account-card-${account.id}`}
              >
                <CardHeader className="border-b-2 border-border p-4 bg-muted/20">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div 
                        className="p-2 border-2"
                        style={{ borderColor: providerInfo.color }}
                      >
                        <ProviderIcon 
                          className="w-6 h-6" 
                          style={{ color: providerInfo.color }} 
                        />
                      </div>
                      <div>
                        <CardTitle className="font-bold text-sm uppercase">
                          {account.account_name || `${providerInfo.label} Account`}
                        </CardTitle>
                        <p className="text-xs text-muted-foreground uppercase">
                          {providerInfo.label}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-4 space-y-4">
                  {/* Status */}
                  <div className="flex items-center gap-2">
                    <StatusIcon 
                      className={`w-4 h-4 ${status.color} ${account.status === 'syncing' ? 'animate-spin' : ''}`} 
                    />
                    <Badge 
                      variant="outline" 
                      className={`text-xs font-bold uppercase ${status.bg} ${status.color} border-current`}
                    >
                      {status.label}
                    </Badge>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 bg-muted/50 border border-border">
                      <span className="text-muted-foreground uppercase">Instances</span>
                      <p className="font-bold text-lg">{account.instance_count || 0}</p>
                    </div>
                    <div className="p-2 bg-muted/50 border border-border">
                      <span className="text-muted-foreground uppercase">Last Sync</span>
                      <p className="font-mono text-xs truncate">
                        {account.last_sync_at 
                          ? new Date(account.last_sync_at).toLocaleDateString() 
                          : "Never"}
                      </p>
                    </div>
                  </div>

                  {/* Error message */}
                  {account.last_error && (
                    <div className="p-2 bg-destructive/10 border border-destructive text-xs text-destructive">
                      {account.last_error}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSync(account.id)}
                      disabled={syncingId === account.id}
                      data-testid={`sync-account-${account.id}`}
                      className="flex-1 border-2 border-secondary text-secondary hover:bg-secondary hover:text-secondary-foreground font-bold uppercase text-xs"
                    >
                      <RefreshCw className={`w-3 h-3 mr-1 ${syncingId === account.id ? 'animate-spin' : ''}`} />
                      Sync
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setAccountToDelete(account);
                        setDeleteDialogOpen(true);
                      }}
                      data-testid={`delete-account-${account.id}`}
                      className="border-2 border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333]">
          <CardContent className="p-12 text-center">
            <div className="flex justify-center gap-4 mb-6">
              {providers.map(p => {
                const Icon = p.icon;
                return (
                  <Icon key={p.value} className="w-8 h-8 text-muted-foreground" />
                );
              })}
            </div>
            <h3 className="font-heading font-bold text-xl uppercase mb-2">
              No Cloud Accounts Connected
            </h3>
            <p className="text-muted-foreground mb-6">
              Add your first cloud account to start monitoring your infrastructure
            </p>
            <Button
              onClick={() => setDialogOpen(true)}
              data-testid="empty-add-account-btn"
              className="bg-primary text-primary-foreground border-2 border-primary font-bold uppercase"
            >
              <Plus className="w-4 h-4 mr-2" />
              ADD YOUR FIRST ACCOUNT
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Add Account Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="bg-card border-2 border-border shadow-[8px_8px_0px_0px_#333] max-w-lg">
          <DialogHeader className="border-b-2 border-border pb-4">
            <DialogTitle className="font-heading font-bold text-xl uppercase">
              Add Cloud Account
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Provider Selection */}
            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider">
                Cloud Provider
              </Label>
              <Select value={selectedProvider} onValueChange={handleProviderChange}>
                <SelectTrigger 
                  className="border-2 border-border bg-input"
                  data-testid="provider-select"
                >
                  <SelectValue placeholder="Select a provider" />
                </SelectTrigger>
                <SelectContent className="bg-card border-2 border-border">
                  {providers.map(p => {
                    const Icon = p.icon;
                    return (
                      <SelectItem 
                        key={p.value} 
                        value={p.value}
                        className="cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4" style={{ color: p.color }} />
                          <span>{p.label}</span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            {/* Account Name */}
            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider">
                Account Name (Optional)
              </Label>
              <Input
                value={accountName}
                onChange={(e) => setAccountName(e.target.value)}
                placeholder="e.g., Production AWS"
                className="border-2 border-border bg-input"
                data-testid="account-name-input"
              />
            </div>

            {/* Credential Fields */}
            {selectedProvider && credentialFields[selectedProvider]?.map(field => (
              <div key={field.key} className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-wider">
                  {field.label}
                </Label>
                {field.type === "textarea" ? (
                  <textarea
                    value={credentials[field.key] || ""}
                    onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className="w-full min-h-[100px] p-3 border-2 border-border bg-input font-mono text-sm"
                    data-testid={`credential-${field.key}`}
                  />
                ) : (
                  <Input
                    type={field.type}
                    value={credentials[field.key] || ""}
                    onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className="border-2 border-border bg-input"
                    data-testid={`credential-${field.key}`}
                  />
                )}
              </div>
            ))}

            {/* Demo Mode Notice */}
            <div className="p-3 bg-secondary/10 border-2 border-secondary text-sm">
              <p className="font-bold text-secondary uppercase text-xs mb-1">Demo Mode</p>
              <p className="text-muted-foreground text-xs">
                For demo purposes, credentials are stored but mock data is generated. 
                Connect real accounts for production use.
              </p>
            </div>
          </div>

          <DialogFooter className="border-t-2 border-border pt-4">
            <Button
              variant="outline"
              onClick={() => { setDialogOpen(false); resetForm(); }}
              className="border-2 border-border"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!selectedProvider || submitting}
              data-testid="submit-account-btn"
              className="bg-primary text-primary-foreground border-2 border-primary font-bold uppercase"
            >
              {submitting ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Adding...</>
              ) : (
                <>Add Account</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-card border-2 border-border shadow-[8px_8px_0px_0px_#333]">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-heading font-bold uppercase">
              Delete Cloud Account?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the cloud account and all associated instances from your inventory.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-2 border-border">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              data-testid="confirm-delete-btn"
              className="bg-destructive text-destructive-foreground border-2 border-destructive"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
