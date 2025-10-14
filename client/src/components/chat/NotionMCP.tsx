import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Plus, Trash2, CheckCircle2, Circle } from "lucide-react";

// Notion logo SVG component
const NotionLogo = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg 
    className={className} 
    viewBox="0 0 24 24" 
    fill="currentColor"
  >
    <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.887-.748-.84l-15.177.887c-.56.047-.747.327-.747.887zm14.336.513c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z"/>
  </svg>
);

interface Workspace {
  workspace_id: string;
  workspace_name: string;
  workspace_icon: string;
  connected?: boolean;
  tools?: any[];
}

interface NotionMCPProps {
  onWorkspaceConnect?: (workspaceId: string, tools: any[]) => void;
  onWorkspacesChange?: (workspaces: Workspace[]) => void;
}

export const NotionMCP = ({ onWorkspaceConnect, onWorkspacesChange }: NotionMCPProps) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(false);
  const [connectingWorkspace, setConnectingWorkspace] = useState<string | null>(null);
  const { toast } = useToast();

  // Load workspaces on mount
  useEffect(() => {
    loadWorkspaces();
    
    // Listen for OAuth success message from popup
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'notion_oauth_success') {
        loadWorkspaces();
        toast({
          title: "Notion connected",
          description: "Workspace connected successfully",
        });
      }
    };
    
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [toast]);

  const loadWorkspaces = async () => {
    try {
      const res = await fetch("/api/notion/workspaces", {
        credentials: "include",
        cache: "no-cache",
      });
      
      if (res.ok) {
        const data = await res.json();
        const newWorkspaces = data.workspaces || [];
        setWorkspaces(newWorkspaces);
        onWorkspacesChange?.(newWorkspaces);
      } else {
        console.warn("Failed to load Notion workspaces:", res.status, res.statusText);
        // Set empty workspaces instead of failing
        setWorkspaces([]);
        onWorkspacesChange?.([]);
      }
    } catch (error) {
      console.error("Failed to load Notion workspaces:", error);
      // Set empty workspaces instead of failing
      setWorkspaces([]);
      onWorkspacesChange?.([]);
    }
  };

  const handleConnectNotion = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/notion/auth", {
        credentials: "include",
      });
      
      const data = await res.json();
      
      if (res.ok && data.oauth_url) {
        // Open OAuth popup
        const width = 600;
        const height = 700;
        const left = (window.screen.width - width) / 2;
        const top = (window.screen.height - height) / 2;
        
        window.open(
          data.oauth_url,
          "Notion OAuth",
          `width=${width},height=${height},left=${left},top=${top}`
        );
      } else {
        toast({
          title: "Configuration error",
          description: data.detail || "Notion OAuth not configured. Please check your .env file.",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Connection failed",
        description: error instanceof Error ? error.message : "Failed to connect to Notion",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleConnectWorkspace = async (workspaceId: string) => {
    setConnectingWorkspace(workspaceId);
    try {
      const res = await fetch(`/api/notion/connect?workspace_id=${workspaceId}`, {
        method: "POST",
        credentials: "include",
        cache: "no-cache",
      });
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error("Connection failed:", res.status, errorText);
        toast({
          title: "Connection failed",
          description: `Server error: ${res.status}`,
          variant: "destructive",
        });
        return;
      }
      
      const data = await res.json();
      
      // Update workspace state
      const updatedWorkspaces = workspaces.map(w => 
        w.workspace_id === workspaceId 
          ? { ...w, connected: true, tools: data.tools }
          : w
      );
      setWorkspaces(updatedWorkspaces);
      onWorkspacesChange?.(updatedWorkspaces);
      
      toast({
        title: "Workspace connected",
        description: `Connected with ${data.tool_count || 0} tools available`,
      });
      
      // Notify parent
      onWorkspaceConnect?.(workspaceId, data.tools || []);
    } catch (error) {
      console.error("Connection error:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setConnectingWorkspace(null);
    }
  };

  const handleDisconnectWorkspace = async (workspaceId: string) => {
    try {
      const res = await fetch(`/api/notion/disconnect/${workspaceId}`, {
        method: "DELETE",
        credentials: "include",
      });
      
      if (res.ok) {
        const updatedWorkspaces = workspaces.filter(w => w.workspace_id !== workspaceId);
        setWorkspaces(updatedWorkspaces);
        onWorkspacesChange?.(updatedWorkspaces);
        
        // Update localStorage
        const connectedIds = updatedWorkspaces
          .filter(w => w.connected)
          .map(w => w.workspace_id);
        localStorage.setItem('connectedNotionWorkspaces', JSON.stringify(connectedIds));
        localStorage.setItem('notionWorkspaces', JSON.stringify(updatedWorkspaces));
        
        toast({
          title: "Workspace disconnected",
          description: "Removed from your account",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to disconnect workspace",
        variant: "destructive",
      });
    }
  };

  return (
    <Card className="bg-card/50 border-border/50 overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-border/50 bg-background/50">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-md bg-black text-white">
            <NotionLogo className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-foreground">Notion MCP</h3>
            <p className="text-xs text-muted-foreground">Multi-workspace support</p>
          </div>
          <Badge variant="secondary" className="text-[10px] px-2 py-0">
            BETA
          </Badge>
        </div>
      </div>

      {/* Content */}
      <div className="p-3 space-y-3">
        {/* Connect Button */}
        <Button
          onClick={handleConnectNotion}
          disabled={loading}
          className="w-full bg-black hover:bg-black/90 text-white h-9 text-sm"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <Plus className="w-4 h-4 mr-2" />
              Connect Workspace
            </>
          )}
        </Button>

        {/* Workspaces List */}
        {workspaces.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground px-1">
              Connected Workspaces
            </p>
            {workspaces.map((workspace) => (
              <div
                key={workspace.workspace_id}
                className="bg-background/80 border border-border/50 rounded-lg p-2.5 space-y-2"
              >
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 text-lg mt-0.5">
                    {workspace.workspace_icon || "📝"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {workspace.workspace_name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {workspace.connected ? (
                        <span className="flex items-center gap-1 text-success">
                          <CheckCircle2 className="w-3 h-3" />
                          Connected
                        </span>
                      ) : (
                        <span className="flex items-center gap-1">
                          <Circle className="w-3 h-3" />
                          Not connected
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex gap-2">
                  {!workspace.connected ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleConnectWorkspace(workspace.workspace_id)}
                      disabled={connectingWorkspace === workspace.workspace_id}
                      className="flex-1 h-7 text-xs"
                    >
                      {connectingWorkspace === workspace.workspace_id ? (
                        <>
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                          Connecting...
                        </>
                      ) : (
                        "Connect"
                      )}
                    </Button>
                  ) : (
                    <div className="flex-1 flex items-center gap-1 text-xs text-muted-foreground px-2">
                      <span>🛠️</span>
                      <span>{workspace.tools?.length || 0} tools</span>
                    </div>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDisconnectWorkspace(workspace.workspace_id)}
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {workspaces.length === 0 && !loading && (
          <div className="text-center py-6 text-muted-foreground">
            <NotionLogo className="w-12 h-12 mx-auto mb-2 opacity-20" />
            <p className="text-xs">No workspaces connected</p>
            <p className="text-xs mt-1">Click above to connect</p>
          </div>
        )}

        {/* Info */}
        <div className="bg-muted/30 border border-border/30 rounded-md p-2 text-xs text-muted-foreground">
          <p className="font-medium mb-1">💡 Quick Tip</p>
          <p>Connect your Notion workspace to query databases and search pages using natural language.</p>
        </div>
      </div>
    </Card>
  );
};
