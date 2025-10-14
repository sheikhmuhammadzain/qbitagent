import { useRef, useEffect } from "react";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Message } from "@/pages/Index";

interface ChatAreaProps {
  connected: boolean;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  notionWorkspaces: any[];
  onMenuClick?: () => void;
}

export const ChatArea = ({ connected, messages, setMessages, notionWorkspaces, onMenuClick }: ChatAreaProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (!messages || messages.length === 0) return;
    const last = messages[messages.length - 1];
    // Avoid auto-scrolling while assistant is streaming to prevent jitter
    if (last?.isStreaming) return;
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex-1 flex flex-col bg-[#212121] min-h-0">
      {/* Mobile Header */}
      {onMenuClick && (
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-white/5">
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="h-9 w-9"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <h1 className="text-sm font-semibold text-foreground">Qbit Agent</h1>
        </div>
      )}
      
      <MessageList messages={messages} messagesEndRef={messagesEndRef} />
      <ChatInput 
        connected={connected} 
        messages={messages}
        setMessages={setMessages}
        notionWorkspaces={notionWorkspaces}
      />
    </div>
  );
};
