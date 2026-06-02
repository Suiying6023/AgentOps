import { useState, useRef, useEffect } from "react";
import { Sparkles, Plus, MessageSquare, PanelLeftClose, PanelLeftOpen, Edit2, Trash2, Check, X } from "lucide-react";

interface SidebarProps {
  threads: {id: string, name: string}[];
  currentThreadId: string | null;
  onLoadThread: (id: string) => void;
  onStartNewThread: () => void;
  onDeleteThread: (id: string) => void;
  onRenameThread: (id: string, newName: string) => void;
}

export function Sidebar({ threads, currentThreadId, onLoadThread, onStartNewThread, onDeleteThread, onRenameThread }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
    }
  }, [editingId]);

  const startEditing = (e: React.MouseEvent, id: string, name: string) => {
    e.stopPropagation();
    setEditingId(id);
    setEditName(name);
  };

  const cancelEditing = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setEditingId(null);
  };

  const saveEditing = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (editingId && editName.trim()) {
      onRenameThread(editingId, editName.trim());
    }
    setEditingId(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      saveEditing();
    } else if (e.key === 'Escape') {
      cancelEditing();
    }
  };

  if (isCollapsed) {
    return (
      <div className="w-14 flex flex-col border-r border-gray-200 bg-[#FAFAFA] items-center py-5 transition-all duration-300">
        <button onClick={() => setIsCollapsed(false)} className="p-2 hover:bg-gray-200 rounded-lg text-gray-500 transition-colors" title="展开侧边栏">
          <PanelLeftOpen size={20} />
        </button>
      </div>
    );
  }

  return (
    <aside className="w-64 flex flex-col border-r border-gray-200 bg-[#FAFAFA] transition-all duration-300 flex-shrink-0">
      <div className="p-5 flex items-center justify-between border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-black text-white rounded-md">
            <Sparkles size={16} />
          </div>
          <h1 className="font-semibold tracking-tight text-gray-900">AgentOps</h1>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={onStartNewThread} className="p-1.5 rounded-md hover:bg-gray-200 transition-colors text-gray-600" title="新对话">
            <Plus size={18} />
          </button>
          <button onClick={() => setIsCollapsed(true)} className="p-1.5 rounded-md hover:bg-gray-200 transition-colors text-gray-600" title="收起侧边栏">
            <PanelLeftClose size={18} />
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="text-xs font-semibold mb-3 px-2 text-gray-400 uppercase tracking-wider">历史会话</div>
        {threads.map((thread) => (
          <div
            key={thread.id}
            onClick={() => {
              if (editingId !== thread.id) onLoadThread(thread.id);
            }}
            className={`group w-full text-left px-3 py-2.5 rounded-lg text-sm flex items-center gap-2 transition-all cursor-pointer ${
              currentThreadId === thread.id 
                ? "bg-gray-200 text-black font-medium"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <MessageSquare size={14} className={currentThreadId === thread.id ? "text-black flex-shrink-0" : "text-gray-400 flex-shrink-0"} />
            
            {editingId === thread.id ? (
              <div className="flex-1 flex items-center gap-1">
                <input
                  ref={inputRef}
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onBlur={() => saveEditing()}
                  className="flex-1 bg-white border border-gray-300 rounded px-1.5 py-0.5 text-sm outline-none w-full"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            ) : (
              <span className="truncate flex-1" title={thread.name}>{thread.name}</span>
            )}

            {editingId !== thread.id && (
              <div className="hidden group-hover:flex items-center gap-1 flex-shrink-0">
                <button
                  onClick={(e) => startEditing(e, thread.id, thread.name)}
                  className="p-1 text-gray-400 hover:text-gray-700 hover:bg-gray-200 rounded"
                  title="重命名"
                >
                  <Edit2 size={12} />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm("确定要删除这个会话吗？")) {
                      onDeleteThread(thread.id);
                    }
                  }}
                  className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                  title="删除"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="p-4 border-t border-gray-200 text-center">
          <span className="text-xs text-gray-400 font-mono tracking-tighter">AGENTOPS V2.0 MONOCHROME</span>
      </div>
    </aside>
  );
}
