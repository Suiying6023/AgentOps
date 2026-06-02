import { useState, useEffect } from "react";
import { Message } from "@/types";
import { api } from "@/lib/api";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [threads, setThreads] = useState<{id: string, name: string}[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [availableModels, setAvailableModels] = useState<{id: string, name: string}[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const savedId = localStorage.getItem('currentThreadId');
    if (savedId) {
      setCurrentThreadId(savedId);
      api.getHistory(savedId)
        .then(setMessages)
        .catch(console.error);
    }
    setIsInitialized(true);
  }, []);

  useEffect(() => {
    api.getThreads().then(setThreads).catch(console.error);
    api.getModels().then(data => {
      if (data.data && data.data.length > 0) {
        setAvailableModels(data.data);
        setSelectedModel(data.data[0].id);
      } else {
        setAvailableModels([]);
        setSelectedModel("");
      }
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      if (currentThreadId) {
        localStorage.setItem('currentThreadId', currentThreadId);
      } else {
        localStorage.removeItem('currentThreadId');
      }
    }
  }, [currentThreadId]);

  const handleDeleteThread = async (id: string) => {
    try {
      await api.deleteThread(id);
      setThreads(prev => prev.filter(t => t.id !== id));
      if (currentThreadId === id) {
        startNewThread();
      }
    } catch (e) {
      console.error(e);
      alert("删除失败");
    }
  };

  const handleRenameThread = async (id: string, newName: string) => {
    try {
      await api.renameThread(id, newName);
      setThreads(prev => prev.map(t => t.id === id ? { ...t, name: newName } : t));
    } catch (e) {
      console.error(e);
      alert("重命名失败");
    }
  };

  const loadThread = async (id: string) => {
    setCurrentThreadId(id);
    setMessages([]);
    try {
      const hist = await api.getHistory(id);
      setMessages(hist);
    } catch (e) {
      console.error(e);
    }
  };

  const startNewThread = () => {
    setCurrentThreadId(null);
    setMessages([]);
  };

  const handleFileUpload = async (file: File, mode: "rag" | "wiki") => {
    setIsUploading(true);
    try {
      await api.uploadKnowledge(file, mode);
    } catch (err) {
      console.error(err);
      alert("上传失败，请检查网络连接");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim()) return;

    if (!selectedModel) {
      alert("未启用模型，无法发送消息，请联系管理员在后台配置可用模型。");
      return;
    }

    let activeThreadId = currentThreadId;
    if (!activeThreadId) {
      activeThreadId = `thread-${Date.now()}`;
      setCurrentThreadId(activeThreadId);
      setThreads(prev => [{id: activeThreadId as string, name: activeThreadId as string}, ...prev]);
    }

    const userMsg: Message = { id: Date.now().toString(), role: "human", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    const startTime = Date.now();

    try {
      const res = await fetch(api.getStreamEndpoint(), {
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

  return {
    messages,
    input,
    setInput,
    isTyping,
    threads,
    currentThreadId,
    selectedModel,
    setSelectedModel,
    availableModels,
    isUploading,
    loadThread,
    startNewThread,
    handleFileUpload,
    handleSubmit,
    handleDeleteThread,
    handleRenameThread
  };
}
