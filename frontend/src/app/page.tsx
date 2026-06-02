"use client";

import { useRef, useEffect } from "react";
import { useChat } from "@/hooks/useChat";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { MessageList } from "@/components/chat/MessageList";
import { ChatInput } from "@/components/chat/ChatInput";

export default function Chat() {
  const chat = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chat.messages]);

  return (
    <div className="flex h-screen font-sans bg-white text-black selection:bg-black selection:text-white">
      <Sidebar 
        threads={chat.threads} 
        currentThreadId={chat.currentThreadId} 
        onLoadThread={chat.loadThread} 
        onStartNewThread={chat.startNewThread} 
        onDeleteThread={chat.handleDeleteThread}
        onRenameThread={chat.handleRenameThread}
      />

      <div className="flex-1 flex flex-col h-screen relative bg-white">
        <Header 
          currentThreadId={chat.currentThreadId} 
        />

        <MessageList 
          messages={chat.messages} 
          isTyping={chat.isTyping} 
          scrollRef={scrollRef} 
        />

        <ChatInput 
          input={chat.input} 
          setInput={chat.setInput} 
          onSubmit={chat.handleSubmit} 
          isTyping={chat.isTyping} 
          isUploading={chat.isUploading} 
          onFileUpload={chat.handleFileUpload} 
          selectedModel={chat.selectedModel} 
          onModelChange={chat.setSelectedModel} 
          availableModels={chat.availableModels} 
        />
      </div>
    </div>
  );
}
