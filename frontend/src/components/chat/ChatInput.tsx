import { useRef } from "react";
import { Send, Paperclip, Loader2, Wand2, ChevronDown } from "lucide-react";

interface ChatInputProps {
  input: string;
  setInput: (val: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isTyping: boolean;
  isUploading: boolean;
  onFileUpload: (file: File, mode: "rag" | "wiki") => void;
  selectedModel: string;
  onModelChange: (model: string) => void;
  availableModels: { id: string; name: string }[];
}

export function ChatInput({ input, setInput, onSubmit, isTyping, isUploading, onFileUpload, selectedModel, onModelChange, availableModels }: ChatInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUploadClick = (mode: "rag" | "wiki") => {
    if (fileInputRef.current) {
      fileInputRef.current.onchange = (e: any) => {
        const file = e.target.files?.[0];
        if (file) {
          onFileUpload(file, mode);
        }
        if (fileInputRef.current) fileInputRef.current.value = "";
      };
      fileInputRef.current.click();
    }
  };

  return (
    <footer className="p-6 bg-white border-t border-gray-100">
      <div className="mx-auto max-w-3xl">
        <form onSubmit={onSubmit} className="relative group flex items-center">
          <input
            type="file"
            className="hidden"
            ref={fileInputRef}
            accept=".txt,.md,.pdf"
          />
          
          <div className="absolute left-2 flex items-center z-10 gap-1 bg-white/90 backdrop-blur pl-1 rounded-l-xl">
              <button
                type="button"
                onClick={() => handleUploadClick("rag")}
                disabled={isTyping || isUploading}
                className="p-2 text-gray-400 hover:text-black transition-colors disabled:opacity-50"
                title="上传资料 (RAG 模式)"
              >
                {isUploading ? <Loader2 size={16} className="animate-spin text-black" /> : <Paperclip size={16} />}
              </button>
              <button
                type="button"
                onClick={() => handleUploadClick("wiki")}
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
            className="w-full pl-20 pr-40 py-4 focus:outline-none transition-all disabled:opacity-50 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 text-[15px] focus:bg-white focus:ring-1 focus:ring-black"
          />
          <div className="absolute right-12 flex items-center gap-2">
            <div className="relative">
                <select 
                    value={selectedModel}
                    onChange={(e) => onModelChange(e.target.value)}
                    disabled={availableModels.length === 0}
                    className="appearance-none bg-transparent border-none text-gray-500 hover:text-black text-[13px] rounded-lg pl-2 pr-6 py-1.5 focus:outline-none cursor-pointer font-medium max-w-[120px] truncate disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {availableModels.length === 0 ? (
                      <option value="">未启用模型</option>
                    ) : (
                      availableModels.map(model => (
                        <option key={model.id} value={model.id}>{model.name}</option>
                      ))
                    )}
                </select>
                <ChevronDown size={14} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>
          </div>
          <button
            type="submit"
            disabled={isTyping || !input.trim() || isUploading || availableModels.length === 0}
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
  );
}
