import { useEffect, useState } from "react";
import { 
  Users, 
  Trash2, 
  RefreshCw,
  Shield,
  Mail,
  Calendar,
  Building2
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getUsers, deleteUser, getAuditEvents } from "@/lib/api";
import { toast } from "sonner";
import { getUser, isAdmin } from "@/components/ProtectedRoute";

const roleColors = {
  admin: "bg-primary text-primary-foreground",
  msp_admin: "bg-accent text-accent-foreground",
  user: "bg-muted text-muted-foreground"
};

export default function Settings() {
  const [users, setUsers] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);
  const [activeTab, setActiveTab] = useState("users");
  const currentUser = getUser();

  const fetchData = async () => {
    try {
      const [usersRes, auditRes] = await Promise.all([
        getUsers(),
        getAuditEvents({ limit: 50 })
      ]);
      setUsers(usersRes.data);
      setAuditEvents(auditRes.data);
    } catch (error) {
      if (error.response?.status !== 403) {
        toast.error("Failed to load data");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDelete = async () => {
    if (!userToDelete) return;
    
    try {
      await deleteUser(userToDelete.id);
      toast.success("User deleted");
      setDeleteDialogOpen(false);
      setUserToDelete(null);
      fetchData();
    } catch (error) {
      toast.error("Failed to delete user");
    }
  };

  if (!isAdmin()) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Card className="bg-card border-2 border-destructive p-8 text-center">
          <Shield className="w-12 h-12 mx-auto mb-4 text-destructive" />
          <h2 className="font-heading font-bold text-xl uppercase mb-2">Access Denied</h2>
          <p className="text-muted-foreground">Admin access required</p>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]" data-testid="settings-loading">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="font-heading font-black text-4xl tracking-tighter uppercase">
          SETTINGS
        </h1>
        <p className="text-muted-foreground text-sm uppercase tracking-wider mt-1">
          User management & audit logs
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-muted border-2 border-border p-1 h-auto">
          <TabsTrigger 
            value="users"
            data-testid="tab-users"
            className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold uppercase text-xs px-4 py-2"
          >
            <Users className="w-4 h-4 mr-2" />
            Users
          </TabsTrigger>
          <TabsTrigger 
            value="audit"
            data-testid="tab-audit"
            className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold uppercase text-xs px-4 py-2"
          >
            <Calendar className="w-4 h-4 mr-2" />
            Audit Log
          </TabsTrigger>
        </TabsList>

        {/* Users Tab */}
        <TabsContent value="users" className="mt-6">
          <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333]">
            <CardHeader className="border-b-2 border-border bg-muted/20 p-4">
              <CardTitle className="font-heading font-bold text-lg uppercase flex items-center gap-2">
                <Users className="w-5 h-5 text-primary" />
                Team Members ({users.length})
              </CardTitle>
            </CardHeader>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-b-2 border-border bg-muted/30 hover:bg-muted/30">
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Name</TableHead>
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Email</TableHead>
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Role</TableHead>
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Last Login</TableHead>
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow 
                      key={user.id}
                      className="border-b border-border/50 hover:bg-muted/20"
                      data-testid={`user-row-${user.id}`}
                    >
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-muted border-2 border-border flex items-center justify-center">
                            <span className="text-xs font-bold">{user.name?.charAt(0)?.toUpperCase()}</span>
                          </div>
                          {user.name}
                          {user.id === currentUser?.id && (
                            <Badge variant="outline" className="text-[10px]">You</Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{user.email}</TableCell>
                      <TableCell>
                        <Badge className={`uppercase text-[10px] font-bold border-0 ${roleColors[user.role] || roleColors.user}`}>
                          {user.role}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {user.last_login_at 
                          ? new Date(user.last_login_at).toLocaleDateString()
                          : "Never"}
                      </TableCell>
                      <TableCell>
                        {user.id !== currentUser?.id && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setUserToDelete(user);
                              setDeleteDialogOpen(true);
                            }}
                            data-testid={`delete-user-${user.id}`}
                            className="border-2 border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        </TabsContent>

        {/* Audit Tab */}
        <TabsContent value="audit" className="mt-6">
          <Card className="bg-card border-2 border-border shadow-[4px_4px_0px_0px_#333]">
            <CardHeader className="border-b-2 border-border bg-muted/20 p-4">
              <CardTitle className="font-heading font-bold text-lg uppercase flex items-center gap-2">
                <Calendar className="w-5 h-5 text-primary" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <div className="overflow-x-auto max-h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow className="border-b-2 border-border bg-muted/30 hover:bg-muted/30">
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Timestamp</TableHead>
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Event</TableHead>
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Entity</TableHead>
                    <TableHead className="font-bold uppercase text-xs tracking-wider">Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditEvents.map((event) => (
                    <TableRow 
                      key={event.id}
                      className="border-b border-border/50 hover:bg-muted/20"
                    >
                      <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(event.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-[10px] uppercase font-mono">
                          {event.event_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        <span className="text-muted-foreground">{event.entity_type}</span>
                        {event.entity_id && (
                          <span className="font-mono text-xs ml-2">{event.entity_id.slice(0, 8)}</span>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs max-w-xs truncate">
                        {JSON.stringify(event.payload || {}).slice(0, 50)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-card border-2 border-border shadow-[8px_8px_0px_0px_#333]">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-heading font-bold uppercase">
              Delete User?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete {userToDelete?.name}'s account. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-2 border-border">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              data-testid="confirm-delete-user-btn"
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
