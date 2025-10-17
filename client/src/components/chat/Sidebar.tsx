import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { FileUpload } from "./FileUpload";
import { DatabaseSelector } from "./DatabaseSelector";
import { NotionMCP } from "./NotionMCP";
import { ChevronLeft, ChevronRight, MessageSquare, Database, Settings, Trash2, Plug, X, LogOut, User, Download, ChevronDown, Upload } from "lucide-react";

import type { Message } from "@/pages/Index";

interface SidebarProps {
  connected: boolean;
  setConnected: (connected: boolean) => void;
  currentModel: string;
  setCurrentModel: (model: string) => void;
  tools: any[];
  setTools: (tools: any[]) => void;
  messageCount: number;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  notionWorkspaces: any[];
  setNotionWorkspaces: (workspaces: any[]) => void;
  onClose?: () => void;
}

export const Sidebar = ({
  connected,
  setConnected,
  currentModel,
  setCurrentModel,
  tools,
  setTools,
  messageCount,
  messages,
  setMessages,
  notionWorkspaces,
  setNotionWorkspaces,
  onClose,
}: SidebarProps) => {
  const [server, setServer] = useState("SQLite");
  const [model, setModel] = useState("z-ai/glm-4.5-air:free");
  const [servers, setServers] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [uploadSectionExpanded, setUploadSectionExpanded] = useState(false);
  const [settingsSectionExpanded, setSettingsSectionExpanded] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    // Fetch current user
    api.me().then((r) => {
      if (r.username) setUsername(r.username);
    }).catch(() => {});
    
    // Fetch dynamic servers and models on mount
    api.servers().then((r) => setServers(r.servers)).catch(() => {});
    api.models().then((r) => setModels(r.models)).catch(() => {});

    // Function to refresh tools
    const refreshTools = async () => {
      try {
        const s = await api.status();
        if (s.tools) {
          setTools(s.tools);
          if (s.connected) setConnected(true);
        }
      } catch (e) {
        console.error("Failed to refresh tools:", e);
      }
    };

    // Initial load
    refreshTools();

    // Refresh tools every 3 seconds to catch Notion/WebSearch additions
    const interval = setInterval(refreshTools, 3000);

    return () => clearInterval(interval);
  }, [setConnected]);

  const modelLabel = useMemo(() => (currentModel ? currentModel.split("/")[1] : "-"), [currentModel]);

  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      const data = await api.connect({ server_name: server });
      setConnected(true);
      // Use the model returned from the API to ensure consistency
      const connectedModel = data.model || model;
      setCurrentModel(connectedModel);
      setTools(data.tools || []);
      toast({ title: "Connected", description: `Connected to ${connectedModel.split("/")[1]}` });
    } catch (error) {
      toast({
        title: "Connection failed",
        description: error instanceof Error ? error.message : "Connection failed",
        variant: "destructive",
      });
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    await api.disconnect();
    setConnected(false);
    setCurrentModel("");
    setTools([]);
    toast({ title: "Disconnected", description: "Successfully disconnected from the server" });
  };

  const handleClearChat = async () => {
    if (!confirm("Are you sure you want to clear all messages? This cannot be undone.")) {
      return;
    }
    
    try {
      await api.clear();
      setMessages([]);
      toast({ title: "Chat cleared", description: "All messages have been cleared" });
    } catch (error) {
      toast({
        title: "Failed to clear chat",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleExportChat = () => {
    if (messages.length === 0) {
      toast({
        title: "No messages to export",
        description: "Start a conversation first",
        variant: "destructive",
      });
      return;
    }

    try {
      // Format messages as JSON
      const exportData = {
        exported_at: new Date().toISOString(),
        username: username,
        model: currentModel,
        message_count: messages.length,
        messages: messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          reasoning: msg.reasoning || null,
          tool_calls: msg.toolCalls?.map(tc => ({
            name: tc.name,
            status: tc.status,
            arguments: tc.arguments,
            result: tc.result,
          })) || [],
        })),
      };

      // Create blob and download
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        title: "Chat exported",
        description: `${messages.length} messages exported successfully`,
      });
    } catch (error) {
      toast({
        title: "Export failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleSignOut = async () => {
    try {
      await api.signout();
      toast({ title: "Signed out", description: "You have been signed out successfully" });
      navigate("/auth");
    } catch (error) {
      toast({
        title: "Sign out failed",
        description: error instanceof Error ? error.message : "Failed to sign out",
        variant: "destructive",
      });
    }
  };

  return (
    <div className={`relative bg-[#212121] border-r border-white/5 flex flex-col transition-all duration-300 h-screen ${isCollapsed ? "w-16" : "w-64 sm:w-72"}`}>
      {/* Collapse/Expand Button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-4 z-10 h-6 w-6 rounded-full bg-[#212121] border border-white/10 hover:bg-[#2b2b2b]"
      >
        {isCollapsed ? (
          <ChevronRight className="h-3 w-3" />
        ) : (
          <ChevronLeft className="h-3 w-3" />
        )}
      </Button>

      {/* Collapsed State - Show icons */}
      {isCollapsed && (
        <div className="flex flex-col items-center py-4 gap-3">
          {/* Connection Status Icon */}
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-lg hover:bg-white/10"
              onClick={() => setIsCollapsed(false)}
            >
              <Plug className={`h-5 w-5 ${connected ? "text-success" : "text-muted-foreground"}`} />
            </Button>
            {connected && (
              <div className="absolute -top-1 -right-1 h-3 w-3 bg-success rounded-full animate-pulse" />
            )}
          </div>

          <Separator className="bg-white/5 w-8" />

          {/* Messages Count */}
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-lg hover:bg-white/10"
              title={`${messageCount} messages`}
            >
              <MessageSquare className="h-5 w-5 text-muted-foreground" />
            </Button>
            {messageCount > 0 && (
              <div className="absolute -top-1 -right-1 h-4 w-4 bg-primary rounded-full flex items-center justify-center">
                <span className="text-[9px] font-bold text-white">{messageCount > 9 ? '9+' : messageCount}</span>
              </div>
            )}
          </div>

          {/* Database Icon */}
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 rounded-lg hover:bg-white/10"
            title={`${tools.length} tools available`}
          >
            <Database className="h-5 w-5 text-muted-foreground" />
          </Button>

          <div className="flex-1" />

          {/* Removed Clear Chat from collapsed sidebar */}

          {/* Settings/Expand */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(false)}
            className="h-10 w-10 rounded-lg hover:bg-white/10"
            title="Expand sidebar"
          >
            <Settings className="h-4 w-4 text-muted-foreground" />
          </Button>
        </div>
      )}

      {!isCollapsed && (
        <>
          <div className="p-4 border-b border-white/5">
            <div className="flex items-center justify-between gap-2 mb-3">
              <h1 onClick={() => navigate("/")} className="text-base sm:text-lg font-semibold cursor-pointer text-foreground">Qbit Agent</h1>
              {/* Close button - Mobile only */}
              {onClose && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onClose}
                  className="h-8 w-8 md:hidden"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <div className={`h-2 w-2 rounded-full ${connected ? "bg-success animate-pulse" : "bg-muted-foreground"}`} />
              <span className="text-xs text-muted-foreground">
                {connected ? "Connected" : "Disconnected"}
              </span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        <div className="bg-card/50 rounded-lg p-3 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Model</span>
            <span className="font-medium text-foreground">{modelLabel}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Tools</span>
            <span className="font-medium text-foreground">{tools.length}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Messages</span>
            <span className="font-medium text-foreground">{messageCount}</span>
          </div>
        </div>
        
        {/* Active Connections Summary */}
        {tools.length > 0 && (() => {
          const sqliteTools = tools.filter(t => t.source === 'SQLite');
          const webSearchTools = tools.filter(t => t.source === 'WebSearch');
          const notionTools = tools.filter(t => t.source?.startsWith('Notion'));
          
          return (
            <div className="bg-card/50 rounded-lg p-3 space-y-2">
              <h3 className="text-xs font-semibold text-muted-foreground mb-2">Active Connections</h3>
              
              {sqliteTools.length > 0 && (
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
                    <span className="text-foreground">SQLite MCP</span>
                  </div>
                  <Badge variant="outline" className="bg-blue-500/20 text-blue-300 border-blue-500/30 text-[10px] h-4">
                    {sqliteTools.length} tools
                  </Badge>
                </div>
              )}
              
              {webSearchTools.length > 0 && (
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
                    <span className="text-foreground">Web Search</span>
                  </div>
                  <Badge variant="outline" className="bg-green-500/20 text-green-300 border-green-500/30 text-[10px] h-4">
                    {webSearchTools.length} tools
                  </Badge>
                </div>
              )}
              
              {notionTools.length > 0 && (
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse" />
                    <span className="text-foreground">Notion MCP</span>
                  </div>
                  <Badge variant="outline" className="bg-purple-500/20 text-purple-300 border-purple-500/30 text-[10px] h-4">
                    {notionTools.length} tools
                  </Badge>
                </div>
              )}
            </div>
          );
        })()}

        {/* Upload Data - Collapsible Section */}
        <div className="border border-white/10 rounded-lg bg-card/30 overflow-hidden">
          <button
            onClick={() => setUploadSectionExpanded(!uploadSectionExpanded)}
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Upload className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Upload Data</span>
            </div>
            <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${uploadSectionExpanded ? 'rotate-180' : ''}`} />
          </button>
          
          {uploadSectionExpanded && (
            <div className="px-4 pb-4">
              <FileUpload
                onUploadSuccess={async (result) => {
                  // Backend now auto-connects after upload - just refresh UI state
                  console.log("Upload success, backend auto-connected to:", result.database_id);
                  
                  // Update connection state immediately (backend is already connected)
                  setConnected(true);
                  
                  // Refresh tools and status to reflect the new database
                  try {
                    const status = await api.status();
                    if (status.tools) {
                      setTools(status.tools);
                      console.log(`✅ Loaded ${status.tools.length} tools after upload`);
                    }
                    if (status.connected) {
                      setConnected(true);
                    }
                  } catch (err) {
                    console.error("Failed to refresh tools after upload:", err);
                  }
                  
                  // Clear chat messages for new database
                  setMessages([]);
                  
                  toast({
                    title: "Database ready",
                    description: `Connected to ${result.database_name}`,
                  });
                }}
              />
            </div>
          )}
        </div>

        <DatabaseSelector
          onDatabaseChange={() => {
            // Clear messages and update status when database changes
            setMessages([]);
          }}
          setConnected={setConnected}
          setTools={setTools}
          setCurrentModel={setCurrentModel}
        />

        {/* Notion MCP Integration */}
        <NotionMCP
          onWorkspaceConnect={(workspaceId, notionTools) => {
            // Update tools list with Notion tools
            setTools(prev => [...prev, ...notionTools]);
            toast({
              title: "Notion workspace connected",
              description: `${notionTools.length} Notion tools available`,
            });
          }}
          onWorkspacesChange={(workspaces) => {
            setNotionWorkspaces(workspaces);
          }}
        />

        <div className="space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">MCP Server</label>
            <Select value={server} onValueChange={setServer} disabled={connected}>
              <SelectTrigger className="h-9 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(servers.length ? servers : ["SQLite"]).map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Model</label>
            <Select value={model} onValueChange={setModel} disabled={connected}>
              <SelectTrigger className="h-9 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(models.length ? models : [
                  "z-ai/glm-4.5-air:free",
                  "anthropic/claude-3.5-sonnet",
                  "anthropic/claude-3.7-sonnet",
                  "deepseek/deepseek-r1",
                  "deepseek/deepseek-reasoner",
                  "openai/gpt-4-turbo",
                  "google/gemini-pro",
                ]).map((m) => (
                  <SelectItem key={m} value={m}>{m}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          {/* Hide manual Connect/Disconnect; auto-connects on mount */}
        </div>

        {tools.length > 0 && (
          <>
            <Separator className="bg-border/50" />
            <div className="space-y-2">
              <div className="flex items-center justify-between px-2">
                <h3 className="text-xs font-semibold text-muted-foreground">Available Tools</h3>
                <Badge variant="outline" className="text-[10px] h-5">{tools.length}</Badge>
              </div>
              <div className="space-y-1">
                {tools.map((tool, index) => {
                  // Determine badge color based on source
                  const getBadgeColor = (source: string) => {
                    if (source?.startsWith('Notion')) return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
                    if (source === 'WebSearch') return 'bg-green-500/20 text-green-300 border-green-500/30';
                    if (source === 'SQLite') return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
                    return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
                  };
                  
                  return (
                    <div key={index} className="bg-card/30 rounded-lg p-2.5 border border-border/30 hover:bg-card/50 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-medium text-xs text-foreground flex-1">{tool.name}</p>
                        {tool.source && (
                          <Badge 
                            variant="outline" 
                            className={`text-[9px] h-4 px-1.5 ${getBadgeColor(tool.source)}`}
                          >
                            {tool.source}
                          </Badge>
                        )}
                      </div>
                      {tool.description && (
                        <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">{tool.description}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
          </div>
          
          {/* Settings Section - Collapsible */}
          <div className="mt-auto p-4 border-t border-white/5">
            <div className="border border-white/10 rounded-lg bg-card/30 overflow-hidden">
              <button
                onClick={() => setSettingsSectionExpanded(!settingsSectionExpanded)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Settings className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Settings</span>
                </div>
                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${settingsSectionExpanded ? 'rotate-180' : ''}`} />
              </button>
              
              {settingsSectionExpanded && (
                <div className="px-4 pb-4 space-y-2">
                  {/* Chat Actions */}
                  {messageCount > 0 && (
                    <div className="space-y-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start h-9 text-sm"
                        onClick={handleExportChat}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        Export Chat
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start h-9 text-sm text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        onClick={handleClearChat}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Clear Chat
                      </Button>
                      <Separator className="bg-white/5" />
                    </div>
                  )}
                  
                  {/* User Info */}
                  {username && (
                    <div className="flex items-center gap-2 px-2 py-1.5 bg-white/5 rounded-lg">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-foreground flex-1 truncate">{username}</span>
                    </div>
                  )}
                  <Button
                    variant="ghost"
                    className="w-full justify-start h-9 text-sm text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    onClick={handleSignOut}
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Sign Out
                  </Button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
