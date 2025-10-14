import { Message } from "./Message";
import type { Message as MessageType } from "@/pages/Index";
import { MessageSquare } from "lucide-react";

interface MessageListProps {
  messages: MessageType[];
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

export const MessageList = ({ messages, messagesEndRef }: MessageListProps) => {
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8 bg-[#212121]">
        <div className="text-center px-4 max-w-md">
          <img src="/herologo2.png" className="h-12 w-12 sm:h-[200px] sm:w-[200px] text-muted-foreground/40 mx-auto" alt="hero logo" />
          <h2 className="text-2xl sm:text-3xl font-semibold text-foreground mb-3">
            How can I help you today?
          </h2>
          <p className="text-sm sm:text-base text-muted-foreground/80 leading-relaxed">
            Ask me anything about your data, run queries, or explore insights with AI-powered assistance
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-[#212121] scrollbar-thin">
      {messages.map((message, index) => (
        <Message key={index} message={message} />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};
