import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Checkbox } from "@/components/ui/checkbox";
import { Send, Square, ChevronDown, Check, Plug } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { Message } from "@/pages/Index";
import { api } from "@/lib/api";

interface ChatInputProps {
  connected: boolean;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  notionWorkspaces?: any[]; // Array of connected Notion workspaces
}

export const ChatInput = ({ connected, messages, setMessages, notionWorkspaces = [] }: ChatInputProps) => {
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const streamRef = useRef<{ close: () => void } | null>(null);
  const { toast } = useToast();
  const [servers, setServers] = useState<string[]>([]);
  const [enabledServers, setEnabledServers] = useState<Set<string>>(new Set(["SQLite", "WebSearch"]));

  // Load available MCP servers and enable WebSearch by default
  useEffect(() => {
    api.servers()
      .then((r) => {
        setServers(r.servers);
        // Enable WebSearch by default since it's always available
        setEnabledServers(prev => {
          const newSet = new Set(prev);
          newSet.add("WebSearch");
          return newSet;
        });
      })
      .catch(() => {});
  }, []);

  // Auto-enable connected Notion workspaces
  useEffect(() => {
    if (notionWorkspaces && notionWorkspaces.length > 0) {
      setEnabledServers(prev => {
        const newSet = new Set(prev);
        let newWorkspacesAdded = false;
        
        notionWorkspaces.forEach(workspace => {
          if (workspace.connected) {
            const notionServerName = `Notion: ${workspace.workspace_name}`;
            if (!prev.has(notionServerName)) {
              newSet.add(notionServerName);
              newWorkspacesAdded = true;
            }
          }
        });
        
        // Show toast only if new workspaces were added
        if (newWorkspacesAdded) {
          toast({
            title: "Notion MCP enabled",
            description: "Notion workspace automatically enabled in chat input",
          });
        }
        
        return newSet;
      });
    }
  }, [notionWorkspaces, toast]);

  const handleSend = async () => {
    if (!input.trim() || !connected || isSending) return;

    const userMessage = {
      role: "user" as const,
      content: input.trim(),
    };

    setMessages([...messages, userMessage]);
    setInput("");
    setIsSending(true);

    try {
      let currentMessages = [...messages, userMessage];
      const assistantMessageIndex = currentMessages.length;

      currentMessages.push({
        role: "assistant" as const,
        content: "",
        isStreaming: true,
        toolCalls: [] as any[],
      });

      setMessages(currentMessages);

      let fullText = "";
      let currentToolCalls: any[] = [];
      let reasoningText = "";

      streamRef.current = api.streamChat(userMessage.content, {
        onEvent: (data) => {
          switch (data.type) {
            case "text_chunk": {
              fullText += data.content;
              setMessages((prev: any[]) => {
                const next = [...prev];
                next[assistantMessageIndex].content = fullText;
                return next;
              });
              break;
            }
            case "tool_call_start": {
              currentToolCalls.push({ name: data.tool_name, status: "starting" });
              setMessages((prev: any[]) => {
                const next = [...prev];
                next[assistantMessageIndex].toolCalls = [...currentToolCalls];
                return next;
              });
              break;
            }
            case "tool_executing": {
              currentToolCalls[currentToolCalls.length - 1] = {
                name: data.tool_name,
                status: "executing",
                arguments: data.arguments,
              };
              setMessages((prev: any[]) => {
                const next = [...prev];
                next[assistantMessageIndex].toolCalls = [...currentToolCalls];
                return next;
              });
              break;
            }
            case "tool_result": {
              currentToolCalls[currentToolCalls.length - 1] = {
                ...currentToolCalls[currentToolCalls.length - 1],
                status: "done",
                result: data.result,
              };
              setMessages((prev: any[]) => {
                const next = [...prev];
                next[assistantMessageIndex].toolCalls = [...currentToolCalls];
                return next;
              });
              break;
            }
            case "synthesizing": {
              // Do not append status text to the content to avoid repetition
              break;
            }
            case "reasoning_chunk": {
              reasoningText += data.content;
              setMessages((prev: any[]) => {
                const next = [...prev];
                next[assistantMessageIndex].reasoning = reasoningText;
                return next;
              });
              break;
            }
            case "reasoning_summary": {
              const summary = `\n\nSummary: ${data.summary}`;
              reasoningText += summary;
              setMessages((prev: any[]) => {
                const next = [...prev];
                next[assistantMessageIndex].reasoning = reasoningText;
                return next;
              });
              break;
            }
            case "reasoning_encrypted": {
              const info = `\n\n[Encrypted reasoning block]`;
              reasoningText += info;
              setMessages((prev: any[]) => {
                const next = [...prev];
                next[assistantMessageIndex].reasoning = reasoningText;
                return next;
              });
              break;
            }
            case "rate_limit": {
              toast({ 
                title: "Rate Limit", 
                description: data.message || "Rate limit hit. Retrying automatically...",
                duration: data.retry_in ? data.retry_in * 1000 : 3000,
              });
              // Don't stop sending - let the retry happen
              break;
            }
            case "timeout": {
              toast({ 
                title: "Timeout", 
                description: data.message || "Request timed out. Retrying...",
                duration: 3000,
              });
              break;
            }
            case "done": {
              setMessages((prev: any[]) => {
                const next = [...prev];
                next[assistantMessageIndex].isStreaming = false;
                if (!next[assistantMessageIndex].content) next[assistantMessageIndex].content = "✓ Done";
                return next;
              });
              setIsSending(false);
              break;
            }
            case "error": {
              toast({ title: "Error", description: data.error, variant: "destructive" });
              setIsSending(false);
              break;
            }
          }
        },
        onError: () => {
          toast({ title: "Stream error", description: "Connection to server lost", variant: "destructive" });
          setIsSending(false);
        },
        onDone: () => {
          setIsSending(false);
        },
      });
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to send message",
        variant: "destructive",
      });
      setIsSending(false);
    }
  };

  const handleStop = () => {
    try {
      streamRef.current?.close();
    } catch {}
    setIsSending(false);
    setMessages((prev: any[]) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.isStreaming) {
        last.isStreaming = false;
        if (!last.content) last.content = "Stopped";
      }
      return next;
    });
  };

  const toggleServer = (server: string) => {
    setEnabledServers(prev => {
      const newSet = new Set(prev);
      if (newSet.has(server)) {
        newSet.delete(server);
        toast({ 
          title: "MCP disabled", 
          description: `${server} is now disabled`,
          variant: "default"
        });
      } else {
        newSet.add(server);
        toast({ 
          title: "MCP enabled", 
          description: `${server} is now active`,
        });
      }
      return newSet;
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-white/5 bg-[#212121] px-4 sm:px-6 py-4">
      <div className="max-w-4xl mx-auto">
        <div className="relative bg-[#2a2a2a]/80 backdrop-blur-sm rounded-2xl border border-white/10 shadow-2xl">
          <div className="flex items-center gap-3 p-3">
            {/* MCP Server toggle - Minimal design */}
            <div className="hidden sm:block">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button 
                    variant="outline" 
                    size="sm"
                    disabled={!connected}
                    className="h-9 px-2.5 text-xs font-medium bg-transparent hover:bg-white/5 border-white/10 gap-1.5 relative"
                  >
                    <Plug className="h-3.5 w-3.5" />
                    <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-primary text-[9px] font-semibold flex items-center justify-center text-primary-foreground">
                      {enabledServers.size}
                    </span>
                    <ChevronDown className="h-3 w-3 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-48 bg-[#2a2a2a] border-white/10" align="start">
                  {(() => {
                    const baseServers = servers.length ? servers : ["SQLite"];
                    const connectedNotionWorkspaces = notionWorkspaces.filter(w => w.connected);
                    const notionServers = connectedNotionWorkspaces.map(w => `Notion: ${w.workspace_name}`);
                    // Always include WebSearch
                    return [...baseServers, ...notionServers, "WebSearch"];
                  })().map((server) => (
                    <DropdownMenuItem
                      key={server}
                      className="flex items-center gap-2 cursor-pointer focus:bg-white/5 px-3 py-2"
                      onSelect={(e) => {
                        e.preventDefault();
                        toggleServer(server);
                      }}
                    >
                      <div className="flex items-center justify-center w-4 h-4 rounded border border-white/20">
                        {enabledServers.has(server) && (
                          <Check className="h-3 w-3 text-primary" />
                        )}
                      </div>
                      <span className="text-sm">{server}</span>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Input field */}
            <div className="flex-1 relative">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={connected ? "Ask anything..." : "Connect to start chatting..."}
                disabled={!connected}
                rows={1}
                className="min-h-[44px] max-h-[200px] w-full resize-none border-0 bg-transparent px-4 py-3 text-sm focus-visible:outline-none focus-visible:ring-0 placeholder:text-muted-foreground/60 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            {/* Send/Stop button */}
            {!isSending ? (
              <Button 
                onClick={handleSend} 
                disabled={!connected || !input.trim()} 
                size="icon" 
                className="h-9 w-9 rounded-lg flex-shrink-0 bg-primary/90 hover:bg-primary disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                <Send className="h-4 w-4" />
              </Button>
            ) : (
              <Button 
                onClick={handleStop} 
                size="icon" 
                className="h-9 w-9 rounded-lg flex-shrink-0 bg-destructive/90 hover:bg-destructive transition-all"
              >
                <Square className="h-3.5 w-3.5 fill-current" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
