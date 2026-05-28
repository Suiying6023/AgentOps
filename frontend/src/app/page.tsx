"use client";

import { useState, useRef, useEffect, useSyncExternalStore } from "react";
import { Send, Sparkles, Bot, User, Wrench, Palette, Clock, Cpu, MessageSquare, Plus } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type Message = {
  id: string;
  role: "human" | "ai" | "system";
  content: string;
  metadata?: {
    latencyMs?: number;
    tokenCount?: number;
  };
};

type ThemeStyle = "future" | "classic";

const THEME_STORAGE_KEY = "agentops_theme";
const THEME_CHANGE_EVENT = "agentops-theme-change";

function readStoredTheme(): ThemeStyle {
  if (typeof window === "undefined") return "classic";
  const saved = localStorage.getItem(THEME_STORAGE_KEY);
  return saved === "future" || saved === "classic" ? saved : "classic";
}

function subscribeToThemeStore(onStoreChange: () => void) {
  if (typeof window === "undefined") return () => {};

  window.addEventListener("storage", onStoreChange);
  window.addEventListener(THEME_CHANGE_EVENT, onStoreChange);

  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(THEME_CHANGE_EVENT, onStoreChange);
  };
}

function writeStoredTheme(theme: ThemeStyle) {
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [threads, setThreads] = useState<string[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const theme = useSyncExternalStore(subscribeToThemeStore, readStoredTheme, () => "classic");
  const scrollRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // 组件加载时获取历史会话列表
  useEffect(() => {
    fetch("http://localhost:8080/threads")
      .then(res => res.json())
      .then(data => setThreads(data))
      .catch(console.error);
  }, []);

  const loadThread = async (id: string) => {
    setCurrentThreadId(id);
    setMessages([]);
    try {
      const res = await fetch("http://localhost:8080/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: id })
      });
      const data = await res.json();
      if (data.messages) {
        setMessages(data.messages.map((m: any, idx: number) => ({
          id: m.run_id || `hist-${idx}`,
          role: m.type === "human" ? "human" : "ai",
          content: m.content,
          metadata: m.metadata
        })));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const startNewThread = () => {
    setCurrentThreadId(null);
    setMessages([]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    let activeThreadId = currentThreadId;
    if (!activeThreadId) {
      // 简单的时间戳生成一个新的 thread ID
      activeThreadId = `thread-${Date.now()}`;
      setCurrentThreadId(activeThreadId);
      setThreads(prev => [activeThreadId as string, ...prev]);
    }

    const userMsg: Message = { id: Date.now().toString(), role: "human", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    const startTime = Date.now();

    try {
      const res = await fetch("http://localhost:8080/graph_agent/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content, stream_tokens: true, thread_id: activeThreadId }),
      });

      if (!res.body) throw new Error("No body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      const aiMsgId = (Date.now() + 1).toString();
      setMessages((prev) => [...prev, { id: aiMsgId, role: "ai", content: "" }]);

      let finalContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "");
            try {
              const data = JSON.parse(dataStr);
              if (data.type === "token" && data.content) {
                 finalContent += data.content;
                 setMessages((prev) => {
                   const newMsgs = [...prev];
                   const lastIndex = newMsgs.length - 1;
                   const last = newMsgs[lastIndex];
                   if (last.id === aiMsgId) {
                     newMsgs[lastIndex] = { ...last, content: last.content + data.content };
                   }
                   return newMsgs;
                 });
              } else if (data.type === "done") {
                setIsTyping(false);
                const latency = Date.now() - startTime;
                const tokenEstimate = Math.ceil(finalContent.length * 1.5);
                setMessages((prev) => {
                   const newMsgs = [...prev];
                   const lastIndex = newMsgs.length - 1;
                   const last = newMsgs[lastIndex];
                   if (last.id === aiMsgId) {
                     newMsgs[lastIndex] = { 
                         ...last, 
                         metadata: { latencyMs: latency, tokenCount: tokenEstimate } 
                     };
                   }
                   return newMsgs;
                 });
              }
            } catch {
                // Parse error ignored
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setIsTyping(false);
    }
  };

  const isFuture = theme === "future";

  return (
    <div className={`flex h-screen font-sans transition-colors duration-500 ${isFuture ? "bg-[#F8FAFC] text-slate-800" : "bg-gray-50 text-gray-900"}`}>
      
      {/* Sidebar 侧边栏 */}
      <aside className={`w-64 flex flex-col transition-colors duration-500 border-r ${
        isFuture ? "bg-white/40 backdrop-blur-xl border-slate-200/60" : "bg-gray-100 border-gray-200"
      }`}>
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg flex items-center justify-center ${isFuture ? "bg-sky-100 text-sky-600 shadow-inner border border-sky-200" : "bg-black text-white rounded-full"}`}>
              <Sparkles size={16} />
            </div>
            <h1 className={`text-base tracking-tight ${isFuture ? "font-semibold text-slate-900" : "font-medium text-gray-800"}`}>AgentOps</h1>
          </div>
          <button onClick={startNewThread} className={`p-1.5 rounded-md transition-colors ${
            isFuture ? "hover:bg-slate-200/50 text-slate-600" : "hover:bg-gray-200 text-gray-600"
          }`} title="新对话">
            <Plus size={18} />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className={`text-xs font-medium mb-2 px-2 ${isFuture ? "text-slate-400" : "text-gray-400"}`}>历史会话</div>
          {threads.map((id) => (
            <button
              key={id}
              onClick={() => loadThread(id)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-sm flex items-center gap-2 transition-all ${
                currentThreadId === id 
                  ? (isFuture ? "bg-sky-50 text-sky-700 shadow-sm border border-sky-100/50" : "bg-white shadow-sm border border-gray-200 text-gray-900")
                  : (isFuture ? "text-slate-600 hover:bg-slate-100/50" : "text-gray-600 hover:bg-gray-200/50")
              }`}
            >
              <MessageSquare size={14} className={currentThreadId === id ? (isFuture ? "text-sky-500" : "text-gray-900") : "text-gray-400"} />
              <span className="truncate flex-1">{id}</span>
            </button>
          ))}
        </div>
        
        <div className="p-4 border-t border-transparent">
           <button 
              onClick={() => writeStoredTheme(isFuture ? "classic" : "future")}
              className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all
                ${isFuture ? "bg-white shadow-sm border border-slate-200 text-slate-600 hover:text-sky-500" : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50"}`}
          >
              <Palette size={16} />
              切换至 {isFuture ? "Classic" : "Future"}
          </button>
        </div>
      </aside>

      {/* Main Chat Area 主聊天区 */}
      <div className="flex-1 flex flex-col h-screen relative">
        <header className={`flex items-center justify-between px-8 py-4 sticky top-0 z-10 transition-colors duration-500
          ${isFuture ? "backdrop-blur-md bg-white/30 border-b border-slate-200/30" : "bg-white/80 backdrop-blur-sm border-b border-gray-100"}
        `}>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${isFuture ? "text-slate-500" : "text-gray-500"}`}>
              {currentThreadId ? `当前会话: ${currentThreadId}` : "新会话 (New Thread)"}
            </span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-8" ref={scrollRef}>
          <div className={`mx-auto space-y-8 ${isFuture ? "max-w-4xl" : "max-w-3xl"}`}>
            <AnimatePresence>
              {messages.length === 0 && (
                <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} className="text-center mt-32">
                  <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-6 
                    ${isFuture ? "bg-white shadow-xl shadow-sky-100 text-sky-500 border border-slate-100" : "bg-black text-white"}`}>
                    <Bot size={32} />
                  </div>
                  <h2 className={`text-2xl mb-3 ${isFuture ? "font-semibold text-slate-800" : "font-medium text-gray-800"}`}>
                    有什么我可以帮忙的？
                  </h2>
                  <p className={`max-w-md mx-auto text-sm leading-relaxed ${isFuture ? "text-slate-500" : "text-gray-500"}`}>
                    点击左侧历史记录或直接发送消息开始新对话。
                  </p>
                </motion.div>
              )}

              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  className={`flex gap-4 ${msg.role === "human" ? "flex-row-reverse" : "flex-row"} ${isFuture ? "" : "group"}`}
                >
                  {/* 头像 */}
                  <div className={`flex-shrink-0 flex items-center justify-center
                    ${isFuture ? "w-10 h-10 rounded-full shadow-sm" : "w-8 h-8 rounded-full mt-1"}
                    ${msg.role === "human" 
                        ? (isFuture ? "bg-slate-900 text-white" : "bg-gray-200 text-gray-600") 
                        : (isFuture ? "bg-white border border-slate-200 text-sky-500" : "border border-gray-200 text-black")}`}>
                    {msg.role === "human" ? <User size={isFuture ? 18 : 16} /> : <Bot size={isFuture ? 18 : 16} />}
                  </div>

                  {/* 气泡内容 */}
                  <div className={`flex flex-col ${isFuture ? "max-w-[80%]" : "max-w-full flex-1"}`}>
                      <div className={`whitespace-pre-wrap leading-relaxed
                        ${isFuture ? "p-5 rounded-3xl shadow-sm text-[15px]" : "py-1.5 text-base"}
                        ${msg.role === "human" 
                          ? (isFuture ? "bg-slate-900 text-slate-50 rounded-tr-sm" : "text-gray-800 bg-gray-100 px-5 py-3 rounded-3xl rounded-tr-sm w-fit ml-auto") 
                          : (isFuture ? "bg-white/90 backdrop-blur-md border border-slate-200/60 text-slate-700 rounded-tl-sm shadow-xl shadow-slate-200/30" : "text-gray-800 bg-transparent")}`}>
                        
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
                                                <div key={idx} className={`my-2 inline-flex w-fit items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border shadow-sm
                                                    ${isFuture ? "bg-sky-50 text-sky-600 border-sky-100" : "bg-gray-50 text-gray-600 border-gray-200"}`}>
                                                    <Wrench size={14} className={isFuture ? "text-sky-500 animate-pulse" : "animate-pulse"} />
                                                    正在调用工具: {toolName}
                                                </div>
                                            );
                                        } else if (part.startsWith('> ✅')) {
                                            return (
                                                <div key={idx} className={`my-1 inline-flex w-fit items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border shadow-sm
                                                    ${isFuture ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-gray-50 text-gray-600 border-gray-200"}`}>
                                                    <Sparkles size={14} className={isFuture ? "text-emerald-500" : ""} />
                                                    工具执行完毕
                                                </div>
                                            );
                                        } else {
                                            return (
                                                <div key={idx} className={`prose max-w-none prose-p:leading-relaxed prose-pre:rounded-xl
                                                    ${isFuture ? "prose-slate prose-sm prose-pre:bg-slate-800 prose-pre:text-slate-100" : "prose-gray text-base prose-pre:bg-gray-100 prose-pre:text-gray-800"}`}>
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                        {part}
                                                    </ReactMarkdown>
                                                </div>
                                            );
                                        }
                                    })}
                                </div>
                            );
                        })()}
                        {isTyping && msg.role === "ai" && msg.id === messages[messages.length-1]?.id && (
                           <span className={`inline-block ml-1 align-middle ${isFuture ? "bg-sky-400 w-2 h-4 animate-pulse" : "bg-gray-400 rounded-full w-2.5 h-2.5 animate-bounce"}`} />
                        )}
                      </div>

                      {msg.role === "ai" && msg.metadata && Object.keys(msg.metadata).length > 0 && (
                          <div className={`mt-2 flex items-center gap-3 text-xs font-medium
                              ${isFuture ? "text-slate-400" : "text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"}`}>
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
              ))}
            </AnimatePresence>
          </div>
        </main>

        <footer className={`p-6 ${isFuture ? "bg-gradient-to-t from-[#F8FAFC] to-transparent" : "bg-white"}`}>
          <div className={`mx-auto ${isFuture ? "max-w-4xl" : "max-w-3xl"}`}>
            <form onSubmit={handleSubmit} className="relative group">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="发送指令..."
                disabled={isTyping}
                className={`w-full px-6 py-4 focus:outline-none transition-all disabled:opacity-50
                  ${isFuture 
                      ? "bg-white/90 backdrop-blur-xl border border-slate-200 rounded-2xl shadow-xl shadow-slate-200/50 focus:ring-2 focus:ring-sky-500/50 text-slate-800 placeholder-slate-400 text-[15px]" 
                      : "bg-gray-100 border-none rounded-3xl text-gray-900 placeholder-gray-500 text-base focus:bg-gray-200"}`}
              />
              <button
                type="submit"
                disabled={isTyping || !input.trim()}
                className={`absolute p-3 transition-colors disabled:opacity-50 shadow-md
                  ${isFuture 
                      ? "right-2 top-2 bg-slate-900 text-white rounded-xl hover:bg-slate-800 disabled:hover:bg-slate-900" 
                      : "right-2 top-1.5 bg-black text-white rounded-full hover:bg-gray-800"}`}
              >
                <Send size={isFuture ? 18 : 16} />
              </button>
            </form>
            <div className="text-center mt-3 text-xs text-gray-400 font-medium flex justify-center items-center gap-2">
              <span>AI 生成内容可能不准确，请审慎参考。</span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
