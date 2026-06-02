"use client";

import { useState, useEffect } from "react";
import { Settings, Save, CheckCircle2, CloudFog, Loader2 } from "lucide-react";

import { api } from "@/lib/api";

type RemoteModel = {
  id: string;
  name: string;
  provider: string;
};

export default function AdminDashboard() {
  const [remoteModels, setRemoteModels] = useState<RemoteModel[]>([]);
  const [enabledModels, setEnabledModels] = useState<Set<string>>(new Set());
  const [reviewModel, setReviewModel] = useState<string>("");
  const [reviewMode, setReviewMode] = useState<string>("sequential");
  const [subagentLow, setSubagentLow] = useState<string>("");
  const [subagentMedium, setSubagentMedium] = useState<string>("");
  const [subagentHigh, setSubagentHigh] = useState<string>("");
  const [isFetching, setIsFetching] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      const data = await api.getSystemConfig();
      if (data.display_models) {
        setEnabledModels(new Set(data.display_models));
      }
      if (data.review_model) {
        setReviewModel(data.review_model);
      }
      if (data.review_mode) {
        setReviewMode(data.review_mode);
      }
      if (data.subagent_model_low) setSubagentLow(data.subagent_model_low);
      if (data.subagent_model_medium) setSubagentMedium(data.subagent_model_medium);
      if (data.subagent_model_high) setSubagentHigh(data.subagent_model_high);
    } catch (e) {
      console.error("Failed to load configs", e);
    }
  };

  const handleFetchRemote = async () => {
    setIsFetching(true);
    try {
      const res = await api.fetchRemoteModels();
      setRemoteModels(res.data || []);
    } catch (e) {
      alert("探测模型列表失败，请检查 .env 中的 API Key 是否正确配置");
    } finally {
      setIsFetching(false);
    }
  };

  const toggleModel = (modelId: string) => {
    const newSet = new Set(enabledModels);
    if (newSet.has(modelId)) {
      newSet.delete(modelId);
    } else {
      newSet.add(modelId);
    }
    setEnabledModels(newSet);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      const modelsArray = Array.from(enabledModels);
      await api.updateSystemConfig("display_models", modelsArray);
      await api.updateSystemConfig("review_model", reviewModel.trim());
      await api.updateSystemConfig("review_mode", reviewMode);
      await api.updateSystemConfig("subagent_model_low", subagentLow.trim());
      await api.updateSystemConfig("subagent_model_medium", subagentMedium.trim());
      await api.updateSystemConfig("subagent_model_high", subagentHigh.trim());
      
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e) {
      alert("保存失败");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex h-screen font-sans bg-[#F9FAFB] text-black selection:bg-black selection:text-white">
      <main className="flex-1 overflow-y-auto bg-[#F9FAFB]">
        <div className="max-w-4xl mx-auto p-10 space-y-8">
          
          <header className="flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-gray-900">系统环境配置</h2>
              <p className="text-gray-500 mt-2 text-sm font-medium">通过探测云端可用模型，利用开关即可快速决定哪些模型对前台用户开放。</p>
            </div>
            <a 
              href="/" 
              className="p-2 text-gray-400 hover:text-black hover:bg-gray-200 bg-gray-100 rounded-lg transition-colors flex items-center justify-center"
              title="返回对话"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            </a>
          </header>

          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden mt-8 p-8 space-y-8">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Settings size={18} className="text-gray-400" />
                  <h3 className="text-lg font-bold text-gray-900">显示模型名单配置</h3>
                </div>
                <button
                  onClick={handleFetchRemote}
                  disabled={isFetching}
                  className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-md hover:bg-gray-800 transition-all disabled:opacity-70"
                >
                  {isFetching ? <Loader2 size={16} className="animate-spin" /> : <CloudFog size={16} />}
                  探测云端可用模型
                </button>
              </div>

              <p className="text-xs text-gray-500">点击按钮探测后，下方将列出通过 .env 环境中配置的各大厂目前能调用的所有模型。勾选后保存，前台即刻生效。</p>
              
              {remoteModels.length > 0 && (
                <div className="mt-4 border border-gray-200 rounded-xl max-h-96 overflow-y-auto bg-gray-50 p-2">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 text-gray-500">
                        <th className="p-3 font-semibold w-1/4">厂商</th>
                        <th className="p-3 font-semibold">模型 ID</th>
                        <th className="p-3 font-semibold text-right w-24">是否启用</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {remoteModels.map((m) => (
                        <tr key={m.id} className="hover:bg-gray-100/50 transition-colors">
                          <td className="p-3 font-medium text-gray-900">{m.provider}</td>
                          <td className="p-3 font-mono text-gray-600">{m.id}</td>
                          <td className="p-3 text-right">
                            <label className="relative inline-flex items-center cursor-pointer">
                              <input 
                                type="checkbox" 
                                className="sr-only peer"
                                checked={enabledModels.has(m.id)}
                                onChange={() => toggleModel(m.id)}
                              />
                              <div className="w-9 h-5 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-black"></div>
                            </label>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="pt-8 border-t border-gray-100 mt-4 space-y-4">
                <label className="block text-sm font-semibold text-gray-700">安全审查配置</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">安全审查模型</label>
                    <select
                      value={reviewModel}
                      onChange={(e) => setReviewModel(e.target.value)}
                      className="w-full p-3 border border-gray-200 rounded-xl bg-gray-50 text-black focus:outline-none focus:ring-2 focus:ring-black text-sm cursor-pointer"
                    >
                      <option value="">-- 请选择审查模型 --</option>
                      {reviewModel && !enabledModels.has(reviewModel) && (
                        <option value={reviewModel}>{reviewModel} (当前, 未开启)</option>
                      )}
                      {Array.from(enabledModels).map(m => (
                        <option key={`review-${m}`} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">审查执行模式</label>
                    <select
                      value={reviewMode}
                      onChange={(e) => setReviewMode(e.target.value)}
                      className="w-full p-3 border border-gray-200 rounded-xl bg-gray-50 text-black focus:outline-none focus:ring-2 focus:ring-black text-sm cursor-pointer"
                    >
                      <option value="sequential">串行执行 (安全稳定，推荐)</option>
                      <option value="parallel">并行执行 (速度最快，需并发API支持)</option>
                      <option value="off">关闭审查 (直接忽略安全性检测)</option>
                    </select>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">用于在后台默默检测用户提示词是否含有恶意注入的专属模型及运行模式策略。</p>
              </div>

              <div className="pt-8 border-t border-gray-100 mt-4 space-y-4">
                <label className="block text-sm font-semibold text-gray-700">子智能体模型配置</label>
                <p className="text-xs text-gray-500">为子智能体分配不同能力层级的专属模型。同样只能从已开启的模型中选择。</p>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">低难度 (Low)</label>
                    <select
                      value={subagentLow}
                      onChange={(e) => setSubagentLow(e.target.value)}
                      className="w-full p-3 border border-gray-200 rounded-xl bg-gray-50 text-black focus:outline-none focus:ring-2 focus:ring-black text-sm cursor-pointer"
                    >
                      <option value="">-- 请选择 --</option>
                      {subagentLow && !enabledModels.has(subagentLow) && <option value={subagentLow}>{subagentLow} (未开启)</option>}
                      {Array.from(enabledModels).map(m => <option key={`low-${m}`} value={m}>{m}</option>)}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">中难度 (Medium)</label>
                    <select
                      value={subagentMedium}
                      onChange={(e) => setSubagentMedium(e.target.value)}
                      className="w-full p-3 border border-gray-200 rounded-xl bg-gray-50 text-black focus:outline-none focus:ring-2 focus:ring-black text-sm cursor-pointer"
                    >
                      <option value="">-- 请选择 --</option>
                      {subagentMedium && !enabledModels.has(subagentMedium) && <option value={subagentMedium}>{subagentMedium} (未开启)</option>}
                      {Array.from(enabledModels).map(m => <option key={`med-${m}`} value={m}>{m}</option>)}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">高难度 (High)</label>
                    <select
                      value={subagentHigh}
                      onChange={(e) => setSubagentHigh(e.target.value)}
                      className="w-full p-3 border border-gray-200 rounded-xl bg-gray-50 text-black focus:outline-none focus:ring-2 focus:ring-black text-sm cursor-pointer"
                    >
                      <option value="">-- 请选择 --</option>
                      {subagentHigh && !enabledModels.has(subagentHigh) && <option value={subagentHigh}>{subagentHigh} (未开启)</option>}
                      {Array.from(enabledModels).map(m => <option key={`high-${m}`} value={m}>{m}</option>)}
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 pt-4">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 bg-black text-white px-6 py-3 rounded-xl text-sm font-semibold shadow-md hover:bg-gray-800 transition-all disabled:opacity-70"
              >
                <Save size={16} />
                {isSaving ? "保存中..." : "保存配置"}
              </button>
              
              {saveSuccess && (
                <span className="text-green-600 flex items-center gap-1.5 text-sm font-medium animate-in fade-in slide-in-from-left-2">
                  <CheckCircle2 size={16} /> 配置已保存
                </span>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
