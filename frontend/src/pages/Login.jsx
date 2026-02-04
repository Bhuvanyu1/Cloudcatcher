import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff, LogIn, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { toast } from "sonner";
import api from "@/lib/api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    setLoading(true);
    try {
      const response = await api.post("/auth/login", { email, password });
      
      // Store tokens and user
      localStorage.setItem("access_token", response.data.access_token);
      localStorage.setItem("refresh_token", response.data.refresh_token);
      localStorage.setItem("user", JSON.stringify(response.data.user));
      
      toast.success(`Welcome back, ${response.data.user.name}!`);
      navigate("/");
    } catch (error) {
      const message = error.response?.data?.detail || "Login failed";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4" data-testid="login-page">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="font-heading font-black text-4xl tracking-tighter uppercase">
            CLOUD<span className="text-primary">WATCHER</span>
          </h1>
          <p className="text-muted-foreground text-sm uppercase tracking-widest mt-2">
            Multi-Cloud Operations Platform
          </p>
        </div>

        <Card className="bg-card border-4 border-primary shadow-[8px_8px_0px_0px_#333]">
          <CardHeader className="border-b-2 border-border pb-4">
            <CardTitle className="font-heading font-bold text-xl uppercase flex items-center gap-2">
              <LogIn className="w-5 h-5 text-primary" />
              Sign In
            </CardTitle>
          </CardHeader>
          
          <form onSubmit={handleLogin}>
            <CardContent className="pt-6 space-y-4">
              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-wider">
                  Email Address
                </Label>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="border-2 border-border bg-input h-12"
                  data-testid="login-email"
                  autoComplete="email"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-wider">
                  Password
                </Label>
                <div className="relative">
                  <Input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="border-2 border-border bg-input h-12 pr-12"
                    data-testid="login-password"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div className="flex justify-end">
                <Link 
                  to="/forgot-password" 
                  className="text-xs text-primary hover:underline uppercase tracking-wider"
                >
                  Forgot Password?
                </Link>
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-4 border-t-2 border-border pt-6">
              <Button
                type="submit"
                disabled={loading}
                data-testid="login-submit"
                className="w-full h-12 bg-primary text-primary-foreground border-2 border-primary hover:border-white font-bold uppercase tracking-wider hard-shadow active-press"
              >
                {loading ? (
                  <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Signing In...</>
                ) : (
                  <>Sign In</>
                )}
              </Button>

              <p className="text-sm text-muted-foreground text-center">
                Don't have an account?{" "}
                <Link to="/register" className="text-primary font-bold hover:underline">
                  Create one
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>

        {/* Demo credentials */}
        <div className="mt-6 p-4 border-2 border-dashed border-border bg-muted/20">
          <p className="text-xs font-bold uppercase text-muted-foreground mb-2">Demo Credentials</p>
          <p className="text-xs font-mono">Email: admin@cloudwatcher.com</p>
          <p className="text-xs font-mono">Password: Admin123!</p>
        </div>
      </div>
    </div>
  );
}
