import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

const Auth = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Get the page user was trying to access
  const from = (location.state as any)?.from?.pathname || "/chat";

  useEffect(() => {
    let isMounted = true;
    
    // Check if already authenticated
    api.me().then((r) => {
      if (isMounted && r.username) {
        navigate(from, { replace: true });
      }
    }).catch(() => {
      // Silently handle auth check failure
    });
    
    return () => {
      isMounted = false;
    };
  }, [navigate, from]);

  const handleSubmit = async () => {
    if (!username || !password) {
      setError("Please enter username and password");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (mode === "signup") {
        await api.signup(username, password);
        toast({
          title: "Account created",
          description: `Welcome, ${username}! Redirecting to chat...`,
        });
      } else {
        await api.signin(username, password);
        toast({
          title: "Signed in",
          description: `Welcome back, ${username}!`,
        });
      }
      
      // Redirect to the page they were trying to access or /chat
      setTimeout(() => navigate(from, { replace: true }), 500);
    } catch (e: any) {
      setError(e?.message || "Authentication failed");
      toast({
        title: "Authentication failed",
        description: e?.message || "Please check your credentials and try again",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#121212] text-foreground flex items-center justify-center p-6">
      <Card className="w-full max-w-md bg-[#1b1b1b] border-white/10 p-6">
        <h1 className="text-xl font-semibold mb-1">{mode === "signin" ? "Sign in" : "Create an account"}</h1>
        <p className="text-sm text-muted-foreground mb-4">Your chats and uploads are kept per account</p>
        <div className="grid gap-2">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            className="h-9 rounded-md bg-[#0f0f0f] border border-white/10 px-3 text-sm outline-none"
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            type="password"
            className="h-9 rounded-md bg-[#0f0f0f] border border-white/10 px-3 text-sm outline-none"
          />
        </div>
        {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
        <div className="mt-4 flex gap-2">
          <Button disabled={loading} onClick={handleSubmit} className="h-9 px-4 text-sm w-full">
            {loading ? "Please wait..." : mode === "signin" ? "Sign in" : "Sign up"}
          </Button>
        </div>
        <div className="mt-3 text-xs text-muted-foreground">
          {mode === "signin" ? (
            <button onClick={() => setMode("signup")} className="underline">Create an account</button>
          ) : (
            <button onClick={() => setMode("signin")} className="underline">I already have an account</button>
          )}
        </div>
      </Card>
    </div>
  );
};

export default Auth;


