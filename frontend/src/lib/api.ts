import { Message } from "@/types";

const BASE_URL = "http://localhost:8080";

export const api = {
  async getThreads(): Promise<{id: string, name: string}[]> {
    const res = await fetch(`${BASE_URL}/history/threads`);
    if (!res.ok) throw new Error("Failed to fetch threads");
    return res.json();
  },

  async deleteThread(threadId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/history/${threadId}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
    });
    if (!res.ok) throw new Error("Failed to delete thread");
  },

  async renameThread(threadId: string, name: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/history/${threadId}/rename`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("token")}`
      },
      body: JSON.stringify({ name })
    });
    if (!res.ok) throw new Error("Failed to rename thread");
  },

  async getModels(): Promise<{ data: { id: string; name: string }[] }> {
    const res = await fetch(`${BASE_URL}/chat/models`);
    if (!res.ok) throw new Error("Failed to fetch models");
    return res.json();
  },

  async getHistory(threadId: string): Promise<Message[]> {
    const res = await fetch(`${BASE_URL}/history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId }),
    });
    if (!res.ok) throw new Error("Failed to fetch history");
    const data = await res.json();
    return (data.messages || []).map((m: any, idx: number) => ({
      id: m.run_id || `hist-${idx}`,
      role: m.type === "human" ? "human" : "ai",
      content: m.content,
      metadata: m.metadata,
    }));
  },

  async uploadKnowledge(file: File, mode: "rag" | "wiki"): Promise<void> {
    const formData = new FormData();
    formData.append("file", file);
    const endpoint = mode === "wiki" ? `${BASE_URL}/knowledge/upload_wiki` : `${BASE_URL}/knowledge/upload`;

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
  },

  getStreamEndpoint(): string {
    return `${BASE_URL}/chat/stream`;
  },

  async getSystemConfig(): Promise<any> {
    const res = await fetch(`${BASE_URL}/admin/config`, {
      headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
    });
    if (!res.ok) throw new Error("Failed to fetch system config");
    return res.json();
  },

  async updateSystemConfig(key: string, value: any): Promise<void> {
    const res = await fetch(`${BASE_URL}/admin/config`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("token")}`
      },
      body: JSON.stringify({ key, value })
    });
    if (!res.ok) throw new Error("Failed to update system config");
  },

  async fetchRemoteModels(): Promise<any> {
    const res = await fetch(`${BASE_URL}/admin/config/fetch-models`, {
      headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
    });
    if (!res.ok) throw new Error("Failed to fetch remote models");
    return res.json();
  }
};
