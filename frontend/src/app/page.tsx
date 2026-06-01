"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Bot, User, Wrench, Clock, Cpu, MessageSquare, Plus, ChevronDown, Paperclip, Loader2, Wand2 } from "lucide-react";
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

// 后端支持的模型列表
const AVAILABLE_MODELS = [
  { id: "", name: "系统默认" },
  { id: "deepseek-chat", name: "DeepSeek V3" },
  { id: "deepseek-reasoner", name: "DeepSeek R1 (深思)" },
  { id: "gpt-4o", name: "GPT-4o (全能)" },
  { id: "gpt-4o-mini", name: "GPT-4o Mini (轻量)" },
  { id: "Qwen/Qwen3-235B-A22B-Instruct-2507", name: "Qwen3 (本地大模型)" }
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [threads, setThreads] = useState<string[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, mode: "rag" | "wiki" = "rag") => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    const endpoint = mode === "wiki" ? "http://localhost:8080/knowledge/upload_wiki" : "http://localhost:8080/knowledge/upload";

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message);
      } else {
        alert("处理失败：" + data.detail);
      }
    } catch (err) {
      console.error(err);
      alert("上传失败，请检查网络连接");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
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
      // 在流式请求中注入当前下拉框选中的 Model，如果不选则传空，由后端 fallback 到默认模型
      const res = await fetch("http://localhost:8080/graph_agent/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            message: userMsg.content, 
            stream_tokens: true, 
            thread_id: activeThreadId,
            model: selectedModel || undefined
        }),
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

  return (
    <div className="flex h-screen font-sans bg-white text-black selection:bg-black selection:text-white">
      
      {/* 极简黑白侧边栏 */}
      <aside className="w-64 flex flex-col border-r border-gray-200 bg-[#FAFAFA]">
        <div className="p-5 flex items-center justify-between border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-black text-white rounded-md">
              <Sparkles size={16} />
            </div>
            <h1 className="font-semibold tracking-tight text-gray-900">AgentOps</h1>
          </div>
          <button onClick={startNewThread} className="p-1.5 rounded-md hover:bg-gray-200 transition-colors text-gray-600" title="新对话">
            <Plus size={18} />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="text-xs font-semibold mb-3 px-2 text-gray-400 uppercase tracking-wider">历史会话</div>
          {threads.map((id) => (
            <button
              key={id}
              onClick={() => loadThread(id)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm flex items-center gap-2 transition-all ${
                currentThreadId === id 
                  ? "bg-gray-200 text-black font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <MessageSquare size={14} className={currentThreadId === id ? "text-black" : "text-gray-400"} />
              <span className="truncate flex-1">{id}</span>
            </button>
          ))}
        </div>
        
        {/* 底部的统一主题信息说明 */}
        <div className="p-4 border-t border-gray-200 text-center">
            <span className="text-xs text-gray-400 font-mono tracking-tighter">AGENTOPS V2.0 MONOCHROME</span>
        </div>
      </aside>

      {/* 主聊天区 */}
      <div className="flex-1 flex flex-col h-screen relative bg-white">
        
        {/* 顶部工具栏（含模型切换） */}
        <header className="flex items-center justify-between px-8 py-4 sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-gray-100">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-500">
              {currentThreadId ? `Thread: ${currentThreadId}` : "New Session"}
            </span>
          </div>
          
          <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-400 uppercase">模型路由</span>
              <div className="relative">
                  <select 
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="appearance-none bg-gray-50 border border-gray-200 text-gray-800 text-sm rounded-lg pl-3 pr-8 py-1.5 focus:outline-none focus:ring-1 focus:ring-black cursor-pointer font-medium"
                  >
                      {AVAILABLE_MODELS.map(model => (
                          <option key={model.id} value={model.id}>{model.name}</option>
                      ))}
                  </select>
                  <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
              </div>
          </div>
        </header>

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

              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-4 group ${msg.role === "human" ? "flex-row-reverse" : "flex-row"}`}
                >
                  {/* 头像 */}
                  <div className={`flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full mt-1
                    ${msg.role === "human" ? "bg-black text-white" : "border border-gray-300 text-black bg-gray-50"}`}>
                    {msg.role === "human" ? <User size={16} /> : <Bot size={16} />}
                  </div>

                  {/* 气泡内容 */}
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
                        {isTyping && msg.role === "ai" && msg.id === messages[messages.length-1]?.id && (
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
              ))}
            </AnimatePresence>
          </div>
        </main>

        <footer className="p-6 bg-white border-t border-gray-100">
          <div className="mx-auto max-w-3xl">
            <form onSubmit={handleSubmit} className="relative group flex items-center">
              <input
                type="file"
                className="hidden"
                ref={fileInputRef}
                onChange={(e) => {
                  // 区分不同文件类型的上传接口
                  // 目前共用一个 ref，通过记录上传类型状态来区分调用
                }}
                accept=".txt,.md,.pdf"
              />
              
              <div className="absolute left-2 flex items-center z-10 gap-1 bg-white/90 backdrop-blur pl-1 rounded-l-xl">
                  <button
                    type="button"
                    onClick={() => {
                        if(fileInputRef.current) {
                            fileInputRef.current.onchange = (e: any) => handleFileUpload(e, "rag");
                            fileInputRef.current.click();
                        }
                    }}
                    disabled={isTyping || isUploading}
                    className="p-2 text-gray-400 hover:text-black transition-colors disabled:opacity-50"
                    title="上传资料 (RAG 模式)"
                  >
                    {isUploading ? <Loader2 size={16} className="animate-spin text-black" /> : <Paperclip size={16} />}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                        if(fileInputRef.current) {
                            fileInputRef.current.onchange = (e: any) => handleFileUpload(e, "wiki");
                            fileInputRef.current.click();
                        }
                    }}
                    disabled={isTyping || isUploading}
                    className="p-2 text-gray-400 hover:text-black transition-colors disabled:opacity-50"
                    title="上传资料 (Wiki 模式)"
                  >
                    <Wand2 size={16} />
                  </button>
              </div>
              
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="发送指令... (左侧可选 RAG 或 Wiki 模式上传资料)"
                disabled={isTyping || isUploading}
                className="w-full pl-20 pr-12 py-4 focus:outline-none transition-all disabled:opacity-50 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 text-[15px] focus:bg-white focus:ring-1 focus:ring-black"
              />
              <button
                type="submit"
                disabled={isTyping || !input.trim() || isUploading}
                className="absolute p-2.5 transition-colors disabled:opacity-50 right-2 bg-black text-white rounded-lg hover:bg-gray-800"
              >
                <Send size={18} />
              </button>
            </form>
            <div className="text-center mt-3 text-[11px] text-gray-400 font-medium">
              Powered by AgentOps Multi-Agent Framework
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
