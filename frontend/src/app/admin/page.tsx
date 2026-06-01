"use client";

import { useState, useEffect } from "react";
import { Key, Server, Activity, Plus, Shield, Cpu, RefreshCw, Edit2, CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";

type ProviderKey = {
  id: string;
  provider: string;
  modelType: string;
  key: string;
  status: "connected" | "error";
  latency: number;
};

export default function AdminDashboard() {
  const [keys, setKeys] = useState<ProviderKey[]>([]);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      // 假设当前为未开启 Bearer Token 的测试环境，开启后需传入 headers: Authorization
      const res = await fetch("http://localhost:8080/admin/providers");
      const data = await res.json();
      setKeys(data.map((item: any) => ({
        id: item.provider,
        provider: item.provider,
        modelType: item.model_type || "N/A",
        key: item.api_key.substring(0, 8) + "******************",
        status: item.status,
        latency: item.latency || 0
      })));
    } catch (e) {
      console.error(e);
    }
  };

  const addNewProvider = async () => {
    const providerName = prompt("请输入厂商名称 (例如 openai, deepseek, siliconflow):");
    if (!providerName) return;
    const apiKey = prompt(`请输入 ${providerName} 的 API Key:`);
    if (!apiKey) return;
    
    setIsUpdating(true);
    try {
      await fetch("http://localhost:8080/admin/providers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: providerName,
          api_key: apiKey,
          model_type: "dynamic",
          base_url: null
        })
      });
      await fetchProviders();
    } catch (e) {
      alert("添加失败");
    } finally {
      setIsUpdating(false);
    }
  };

  const deleteProvider = async (provider: string) => {
    if (!confirm(`确定要移除 ${provider} 的配置吗？`)) return;
    try {
      await fetch(`http://localhost:8080/admin/providers/${provider}`, { method: "DELETE" });
      await fetchProviders();
    } catch (e) {
      alert("删除失败");
    }
  };

  return (
    <div className="flex h-screen font-sans bg-[#F9FAFB] text-black selection:bg-black selection:text-white">
      
      {/* 侧边栏 */}
      <aside className="w-64 flex flex-col border-r border-gray-200 bg-white shadow-sm z-10">
        <div className="p-6 flex items-center gap-3 border-b border-gray-100">
          <div className="p-2 bg-black text-white rounded-lg shadow-md">
            <Shield size={18} />
          </div>
          <h1 className="font-bold text-lg tracking-tight text-gray-900">管理页面</h1>
        </div>
        
        <div className="flex-1 p-4 space-y-2">
          <div className="text-xs font-semibold mb-3 px-3 text-gray-400 uppercase tracking-wider">系统配置</div>
          <button className="w-full text-left px-4 py-3 rounded-xl text-sm flex items-center gap-3 bg-gray-100 text-black font-semibold transition-all">
            <Server size={16} /> 上游模型网关
          </button>
          <button className="w-full text-left px-4 py-3 rounded-xl text-sm flex items-center gap-3 text-gray-500 hover:bg-gray-50 hover:text-black font-medium transition-all">
            <Activity size={16} /> 成本与 Token 监控
          </button>
        </div>
        
        <div className="p-6 border-t border-gray-100 text-center">
            <span className="text-[11px] text-gray-400 font-mono tracking-tighter bg-gray-50 px-3 py-1.5 rounded-full border border-gray-200">
              AGENTOPS V2.0
            </span>
        </div>
      </aside>

      {/* 主面板区 */}
      <main className="flex-1 overflow-y-auto bg-[#F9FAFB]">
        <div className="max-w-5xl mx-auto p-10 space-y-8">
          
          <header>
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">模型网关配置</h2>
            <p className="text-gray-500 mt-2 text-sm font-medium">管理大模型厂商的 API Key 与网络连通性。</p>
          </header>

          {/* 核心指标卡片 */}
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow cursor-default">
              <div className="flex items-center gap-3 text-gray-500 mb-4">
                <div className="p-2 bg-gray-50 rounded-lg"><Server size={18} className="text-black" /></div>
                <span className="text-sm font-semibold uppercase tracking-wider">已接入厂商</span>
              </div>
              <div className="text-4xl font-black text-gray-900">{keys.length}</div>
            </div>
            
            <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow cursor-default">
              <div className="flex items-center gap-3 text-gray-500 mb-4">
                <div className="p-2 bg-gray-50 rounded-lg"><Activity size={18} className="text-black" /></div>
                <span className="text-sm font-semibold uppercase tracking-wider">网关平均延迟</span>
              </div>
              <div className="text-4xl font-black text-gray-900">
                {Math.round(keys.filter(k => k.status === 'connected').reduce((acc, curr) => acc + curr.latency, 0) / (keys.filter(k => k.status === 'connected').length || 1))} ms
              </div>
            </div>

            <div className="bg-black text-white p-6 rounded-2xl shadow-xl flex flex-col justify-between relative overflow-hidden group">
              <div className="absolute -right-4 -top-4 w-24 h-24 bg-white/10 rounded-full blur-2xl group-hover:bg-white/20 transition-colors"></div>
              <div className="flex items-center gap-3 text-gray-300 mb-4 relative z-10">
                <div className="p-2 bg-white/10 rounded-lg"><Cpu size={18} className="text-white" /></div>
                <span className="text-sm font-semibold uppercase tracking-wider">主脑路由状态</span>
              </div>
              <div className="text-4xl font-black text-white relative z-10 flex items-center gap-3">
                <span className="w-3 h-3 bg-green-400 rounded-full shadow-[0_0_15px_rgba(74,222,128,0.5)] animate-pulse"></span>
                ACTIVE
              </div>
            </div>
          </div>

          {/* API Key 管理列表 */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden mt-8">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                API 密钥列表
              </h3>
              <button 
                onClick={addNewProvider}
                disabled={isUpdating}
                className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-md hover:bg-gray-800 transition-colors disabled:opacity-70"
              >
                {isUpdating ? <RefreshCw size={16} className="animate-spin" /> : <Plus size={16} />}
                添加供应商 Key
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-white border-b border-gray-100 text-xs uppercase tracking-wider text-gray-500 font-semibold">
                    <th className="p-5 font-semibold">供应商平台</th>
                    <th className="p-5 font-semibold">支持模型映射</th>
                    <th className="p-5 font-semibold">API Key</th>
                    <th className="p-5 font-semibold">连通性状态</th>
                    <th className="p-5 font-semibold">延迟</th>
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
                      <td className="p-5 font-bold text-gray-900 flex items-center gap-2">
                        {k.provider}
                      </td>
                      <td className="p-5">
                        <div className="flex flex-wrap gap-1.5">
                          {k.modelType.split(',').map(m => (
                            <span key={m} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs font-semibold rounded-md border border-gray-200">
                              {m.trim()}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="p-5">
                        <code className="bg-gray-100 px-2.5 py-1.5 rounded-md text-sm font-mono text-gray-500 border border-gray-200 select-all">{k.key}</code>
                      </td>
                      <td className="p-5">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                          k.status === 'connected' 
                            ? "bg-green-50 text-green-700 border border-green-200" 
                            : "bg-red-50 text-red-700 border border-red-200"
                        }`}>
                          {k.status === 'connected' ? <CheckCircle2 size={12} /> : null}
                          {k.status === 'connected' ? '已连接' : '不可用'}
                        </span>
                      </td>
                      <td className="p-5 text-gray-900 font-medium">
                        {k.latency > 0 ? `${k.latency}ms` : '-'}
                      </td>
                      <td className="p-5 text-right">
                        <button 
                          onClick={() => deleteProvider(k.provider)}
                          className="text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors flex items-center gap-1.5 ml-auto opacity-0 group-hover:opacity-100"
                        >
                          <Edit2 size={14} /> 移除配置
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
