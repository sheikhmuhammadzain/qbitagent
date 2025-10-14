import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/chat/Sidebar";
import { ChatArea } from "@/components/chat/ChatArea";

export type Message = {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  reasoning?: string;
  toolCalls?: Array<{
    name: string;
    status: "starting" | "executing" | "done";
    arguments?: any;
    result?: string;
  }>;
};

const Index = () => {
  const navigate = useNavigate();
  const [connected, setConnected] = useState(false);
  const [currentModel, setCurrentModel] = useState("");
  const [tools, setTools] = useState<any[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [notionWorkspaces, setNotionWorkspaces] = useState<any[]>([]);

  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Protect route: redirect to /auth if not signed in
  useEffect(() => {
    fetch("/api/auth/me").then(async (r) => {
      const data = await r.json();
      if (!data.username) navigate("/auth");
    }).catch(() => navigate("/auth"));
  }, [navigate]);

  // Restore state from localStorage and load chat history
  useEffect(() => {
    (async () => {
      try {
        // Restore Notion workspaces from localStorage
        const savedNotionWorkspaces = localStorage.getItem('notionWorkspaces');
        if (savedNotionWorkspaces) {
          try {
            const workspaces = JSON.parse(savedNotionWorkspaces);
            setNotionWorkspaces(workspaces);
          } catch (e) {
            console.error('Failed to parse saved Notion workspaces:', e);
          }
        }

        // Load chat history from backend
        const h = await api.history(50);
        if (h.messages && h.messages.length) {
          setMessages(
            h.messages
              .filter((m) => m.role === "user" || m.role === "assistant")
              .map((m) => ({ role: m.role as any, content: m.content }))
          );
        }

        // Restore connection status if tools are available
        const status = await api.status();
        if (status.tools && status.tools.length > 0) {
          setTools(status.tools);
          setConnected(true);
          // Set current model from status
          if (status.model) {
            setCurrentModel(status.model);
          }
        }
      } catch (error) {
        console.error('Failed to restore state:', error);
      }
    })();
  }, []);

  return (
    <div className="flex h-screen w-full bg-[#212121] overflow-hidden">
      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Sidebar - Hidden on mobile by default */}
      <div className={`fixed md:relative inset-y-0 left-0 z-50 md:z-0 transform transition-transform duration-300 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      }`}>
        <Sidebar
          connected={connected}
          setConnected={setConnected}
          currentModel={currentModel}
          setCurrentModel={setCurrentModel}
          tools={tools}
          setTools={setTools}
          messageCount={messages.length}
          messages={messages}
          setMessages={setMessages}
          notionWorkspaces={notionWorkspaces}
          setNotionWorkspaces={setNotionWorkspaces}
          onClose={() => setSidebarOpen(false)}
        />
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        <ChatArea
          connected={connected}
          messages={messages}
          setMessages={setMessages}
          notionWorkspaces={notionWorkspaces}
          onMenuClick={() => setSidebarOpen(true)}
        />
      </div>
    </div>
  );
};

export default Index;
