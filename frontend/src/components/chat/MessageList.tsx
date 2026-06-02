import { RefObject } from "react";
import { Message } from "@/types";
import { ChatMessage } from "./ChatMessage";
import { AnimatePresence, motion } from "framer-motion";
import { Bot } from "lucide-react";

interface MessageListProps {
  messages: Message[];
  isTyping: boolean;
  scrollRef: RefObject<HTMLDivElement | null>;
}

export function MessageList({ messages, isTyping, scrollRef }: MessageListProps) {
  return (
    <main className="flex-1 overflow-y-auto px-4 py-8" ref={scrollRef}>
      <div className="mx-auto max-w-3xl space-y-8">
        <AnimatePresence>
          {messages.length === 0 && (
            <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} className="text-center mt-32">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-6 bg-black text-white">
                <Bot size={32} />
              </div>
              <h2 className="text-2xl mb-3 font-semibold text-gray-900 tracking-tight">
                系统就绪
              </h2>
              <p className="max-w-md mx-auto text-sm leading-relaxed text-gray-500">
                在上方切换模型，或直接提问。系统将根据任务自动分配相应的子智能体。
              </p>
            </motion.div>
          )}

          {messages.map((msg, idx) => (
            <ChatMessage 
              key={msg.id} 
              msg={msg} 
              isLast={idx === messages.length - 1} 
              isTyping={isTyping} 
            />
          ))}
        </AnimatePresence>
      </div>
    </main>
  );
}
