"use client";

import { useState, useEffect } from "react";
import { Key, Users, Activity, Plus, Shield, Cpu, RefreshCw, XCircle } from "lucide-react";
import { motion } from "framer-motion";

type ApiKey = {
  id: string;
  name: string;
  key: string;
  createdAt: string;
  status: "active" | "revoked";
  usage: number;
};

export default function AdminDashboard() {
  const [keys, setKeys] = useState<ApiKey[]>([
    { id: "1", name: "Default Tenant", key: "sk-agentops-******************", createdAt: "2026-06-01", status: "active", usage: 14523 },
    { id: "2", name: "Marketing Dept", key: "sk-agentops-******************", createdAt: "2026-06-01", status: "active", usage: 892 },
    { id: "3", name: "External Vendor", key: "sk-agentops-******************", createdAt: "2026-05-28", status: "revoked", usage: 34000 }
  ]);
  
  const [isGenerating, setIsGenerating] = useState(false);

  const generateNewKey = () => {
    setIsGenerating(true);
    setTimeout(() => {
      const newKey: ApiKey = {
        id: Date.now().toString(),
        name: `Tenant ${keys.length + 1}`,
        key: `sk-agentops-${Math.random().toString(36).substr(2, 10)}${Math.random().toString(36).substr(2, 10)}`,
        createdAt: new Date().toISOString().split('T')[0],
        status: "active",
        usage: 0
      };
      setKeys([newKey, ...keys]);
      setIsGenerating(false);
    }, 600);
  };

  const revokeKey = (id: string) => {
    setKeys(keys.map(k => k.id === id ? { ...k, status: "revoked" } : k));
  };

  return (
    <div className="flex h-screen font-sans bg-[#F9FAFB] text-black selection:bg-black selection:text-white">
      
      {/* 极简黑白侧边栏 */}
      <aside className="w-64 flex flex-col border-r border-gray-200 bg-white shadow-sm z-10">
        <div className="p-6 flex items-center gap-3 border-b border-gray-100">
          <div className="p-2 bg-black text-white rounded-lg shadow-md">
            <Shield size={18} />
          </div>
          <h1 className="font-bold text-lg tracking-tight text-gray-900">Admin Console</h1>
        </div>
        
        <div className="flex-1 p-4 space-y-2">
          <div className="text-xs font-semibold mb-3 px-3 text-gray-400 uppercase tracking-wider">系统管理</div>
          <button className="w-full text-left px-4 py-3 rounded-xl text-sm flex items-center gap-3 bg-gray-100 text-black font-semibold transition-all">
            <Key size={16} /> API Keys 网关
          </button>
          <button className="w-full text-left px-4 py-3 rounded-xl text-sm flex items-center gap-3 text-gray-500 hover:bg-gray-50 hover:text-black font-medium transition-all">
            <Activity size={16} /> 资源监控
          </button>
          <button className="w-full text-left px-4 py-3 rounded-xl text-sm flex items-center gap-3 text-gray-500 hover:bg-gray-50 hover:text-black font-medium transition-all">
            <Users size={16} /> 租户分配
          </button>
        </div>
        
        <div className="p-6 border-t border-gray-100 text-center">
            <span className="text-[11px] text-gray-400 font-mono tracking-tighter bg-gray-50 px-3 py-1.5 rounded-full border border-gray-200">
              AGENTOPS MONOCHROME
            </span>
        </div>
      </aside>

      {/* 主面板区 */}
      <main className="flex-1 overflow-y-auto bg-[#F9FAFB]">
        <div className="max-w-5xl mx-auto p-10 space-y-8">
          
          <header>
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">动态网关总览</h2>
            <p className="text-gray-500 mt-2 text-sm font-medium">统一管理所有下游租户的 API 密钥与模型额度调度。</p>
          </header>

          {/* 核心指标卡片 */}
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow cursor-default">
              <div className="flex items-center gap-3 text-gray-500 mb-4">
                <div className="p-2 bg-gray-50 rounded-lg"><Key size={18} className="text-black" /></div>
                <span className="text-sm font-semibold uppercase tracking-wider">活跃 API Keys</span>
              </div>
              <div className="text-4xl font-black text-gray-900">{keys.filter(k => k.status === 'active').length}</div>
            </div>
            
            <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow cursor-default">
              <div className="flex items-center gap-3 text-gray-500 mb-4">
                <div className="p-2 bg-gray-50 rounded-lg"><Cpu size={18} className="text-black" /></div>
                <span className="text-sm font-semibold uppercase tracking-wider">总计 Token 消耗</span>
              </div>
              <div className="text-4xl font-black text-gray-900">{keys.reduce((acc, curr) => acc + curr.usage, 0).toLocaleString()}</div>
            </div>

            <div className="bg-black text-white p-6 rounded-2xl shadow-xl flex flex-col justify-between relative overflow-hidden group">
              <div className="absolute -right-4 -top-4 w-24 h-24 bg-white/10 rounded-full blur-2xl group-hover:bg-white/20 transition-colors"></div>
              <div className="flex items-center gap-3 text-gray-300 mb-4 relative z-10">
                <div className="p-2 bg-white/10 rounded-lg"><Activity size={18} className="text-white" /></div>
                <span className="text-sm font-semibold uppercase tracking-wider">网关状态</span>
              </div>
              <div className="text-4xl font-black text-white relative z-10 flex items-center gap-3">
                <span className="w-3 h-3 bg-green-400 rounded-full shadow-[0_0_15px_rgba(74,222,128,0.5)] animate-pulse"></span>
                RUNNING
              </div>
            </div>
          </div>

          {/* API Key 管理列表 */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden mt-8">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                密钥分配大盘
              </h3>
              <button 
                onClick={generateNewKey}
                disabled={isGenerating}
                className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-md hover:bg-gray-800 transition-colors disabled:opacity-70"
              >
                {isGenerating ? <RefreshCw size={16} className="animate-spin" /> : <Plus size={16} />}
                {isGenerating ? "生成中..." : "下发新密钥"}
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-white border-b border-gray-100 text-xs uppercase tracking-wider text-gray-500 font-semibold">
                    <th className="p-5 font-semibold">租户名称 (Tenant)</th>
                    <th className="p-5 font-semibold">API Key</th>
                    <th className="p-5 font-semibold">生成日期</th>
                    <th className="p-5 font-semibold">Token 消耗</th>
                    <th className="p-5 font-semibold">状态</th>
                    <th className="p-5 font-semibold text-right">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {keys.map((k) => (
                    <motion.tr 
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      key={k.id} 
                      className="hover:bg-gray-50 transition-colors group"
                    >
                      <td className="p-5 font-semibold text-gray-900">{k.name}</td>
                      <td className="p-5">
                        <code className="bg-gray-100 px-2.5 py-1.5 rounded-md text-sm font-mono text-gray-600 border border-gray-200">{k.key}</code>
                      </td>
                      <td className="p-5 text-gray-500 font-medium text-sm">{k.createdAt}</td>
                      <td className="p-5 text-gray-900 font-bold">{k.usage.toLocaleString()}</td>
                      <td className="p-5">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                          k.status === 'active' 
                            ? "bg-green-50 text-green-700 border border-green-200" 
                            : "bg-gray-100 text-gray-500 border border-gray-200"
                        }`}>
                          {k.status === 'active' ? <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> : null}
                          {k.status}
                        </span>
                      </td>
                      <td className="p-5 text-right">
                        {k.status === 'active' && (
                          <button 
                            onClick={() => revokeKey(k.id)}
                            className="text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors flex items-center gap-1.5 ml-auto opacity-0 group-hover:opacity-100"
                          >
                            <XCircle size={14} /> 吊销
                          </button>
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
            {keys.length === 0 && (
                <div className="p-10 text-center text-gray-500 font-medium">暂无 API Key，请点击上方按钮生成。</div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
