export type MessageRole = "human" | "ai" | "system";

export type MessageMetadata = {
  latencyMs?: number;
  tokenCount?: number;
};

export type Message = {
  id: string;
  role: MessageRole;
  content: string;
  metadata?: MessageMetadata;
};

export type ModelProvider = {
  id: string;
  name: string;
  provider?: string;
};
