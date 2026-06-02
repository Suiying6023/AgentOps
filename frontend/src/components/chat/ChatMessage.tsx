import { Bot, User, Wrench, Sparkles, Clock, Cpu } from "lucide-react";
import { motion } from "framer-motion";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from "@/types";

interface ChatMessageProps {
  msg: Message;
  isLast: boolean;
  isTyping: boolean;
}

export function ChatMessage({ msg, isLast, isTyping }: ChatMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-4 group ${msg.role === "human" ? "flex-row-reverse" : "flex-row"}`}
    >
      <div className={`flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full mt-1
        ${msg.role === "human" ? "bg-black text-white" : "border border-gray-300 text-black bg-gray-50"}`}>
        {msg.role === "human" ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className="flex flex-col flex-1 max-w-full">
          <div className={`whitespace-pre-wrap leading-relaxed py-1.5 text-[15px]
            ${msg.role === "human" 
              ? "text-black bg-gray-100 px-5 py-3 rounded-2xl rounded-tr-sm w-fit ml-auto" 
              : "text-gray-900 bg-transparent"}`}>
            
            {(() => {
                if (msg.role === "human") return msg.content;
                
                const parts = msg.content.split(/(> ⚙️ \*\*\[系统日志\] 正在调用工具\*\*: `[\s\S]*?`\n> \*\*参数\*\*: `[\s\S]*?`|> ✅ \*\*\[系统日志\] 工具执行完毕\*\*)/g);
                
                return (
                    <div className="flex flex-col">
                        {parts.map((part, idx) => {
                            if (!part.trim()) return null;
                            
                            if (part.startsWith('> ⚙️')) {
                                const match = part.match(/> ⚙️ \*\*\[系统日志\] 正在调用工具\*\*: `(.*?)`/);
                                const toolName = match ? match[1] : '未知工具';
                                return (
                                    <div key={idx} className="my-2 inline-flex w-fit items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-200 bg-gray-50 text-gray-700">
                                        <Wrench size={12} className="animate-pulse text-gray-900" />
                                        调用工具: {toolName}
                                    </div>
                                );
                            } else if (part.startsWith('> ✅')) {
                                return (
                                    <div key={idx} className="my-1 inline-flex w-fit items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-200 bg-gray-50 text-gray-700">
                                        <Sparkles size={12} className="text-black" />
                                        工具执行完毕
                                    </div>
                                );
                            } else {
                                return (
                                    <div key={idx} className="prose prose-slate max-w-none leading-relaxed text-[15px] text-gray-800 prose-p:m-0 prose-p:mb-1.5 prose-headings:m-0 prose-headings:mt-4 prose-headings:mb-2 prose-headings:font-semibold prose-ul:m-0 prose-ul:mb-1.5 prose-ul:pl-5 prose-ol:m-0 prose-ol:mb-1.5 prose-ol:pl-5 prose-li:m-0 prose-li:mb-0.5 prose-code:px-1.5 prose-code:py-0.5 prose-code:bg-gray-100 prose-code:text-gray-800 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none prose-pre:my-2 prose-pre:rounded-lg prose-pre:bg-gray-50 prose-pre:text-gray-900 prose-pre:border prose-pre:border-gray-200 prose-strong:font-semibold prose-strong:text-gray-900 prose-table:w-full prose-table:border-collapse prose-th:border prose-th:border-gray-200 prose-th:bg-gray-50 prose-th:px-3 prose-th:py-2 prose-td:border prose-td:border-gray-200 prose-td:px-3 prose-td:py-2">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {part.replace(/\n{3,}/g, '\n\n')}
                                        </ReactMarkdown>
                                    </div>
                                );
                            }
                        })}
                    </div>
                );
            })()}
            {isTyping && msg.role === "ai" && isLast && (
               <span className="inline-block ml-1 align-middle bg-black rounded-sm w-2 h-4 animate-pulse" />
            )}
          </div>

          {msg.role === "ai" && msg.metadata && Object.keys(msg.metadata).length > 0 && (
              <div className="mt-2 flex items-center gap-3 text-xs font-medium text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
                  {msg.metadata.latencyMs && (
                      <span className="flex items-center gap-1">
                          <Clock size={12} /> {(msg.metadata.latencyMs / 1000).toFixed(2)}s
                      </span>
                  )}
                  {msg.metadata.tokenCount && (
                      <span className="flex items-center gap-1">
                          <Cpu size={12} /> ~{msg.metadata.tokenCount} tokens
                      </span>
                  )}
              </div>
          )}
      </div>
    </motion.div>
  );
}
