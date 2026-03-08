import { useState, useRef, useCallback, useEffect } from "react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  toolCalls?: ToolCallInfo[];
  streaming?: boolean;
}

export interface ToolCallInfo {
  name: string;
  status: "running" | "done" | "error";
  result?: string;
}

interface WsEvent {
  type: "text" | "tool_start" | "tool_end" | "thinking" | "done" | "error";
  content?: string;
  tool?: string;
  input?: Record<string, unknown>;
  result?: string;
  conversation_id?: number;
  message?: string;
}

export function useChat(token: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingMsgIdRef = useRef<string | null>(null);

  const sendMessage = useCallback(
    async (userInput: string) => {
      if (!userInput.trim() || isLoading) return;
      setError(null);

      // Ajouter le message utilisateur
      const userId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        { id: userId, role: "user", content: userInput },
      ]);

      // Préparer le message assistant (streaming)
      const assistantId = crypto.randomUUID();
      pendingMsgIdRef.current = assistantId;
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "", streaming: true, toolCalls: [] },
      ]);

      setIsLoading(true);

      // WebSocket
      const wsUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/chat`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            message: userInput,
            conversation_id: conversationId,
            token,
          })
        );
      };

      ws.onmessage = (event) => {
        const data: WsEvent = JSON.parse(event.data);
        const aid = pendingMsgIdRef.current;
        if (!aid) return;

        switch (data.type) {
          case "text":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aid ? { ...m, content: m.content + (data.content ?? "") } : m
              )
            );
            break;

          case "thinking":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aid
                  ? { ...m, thinking: (m.thinking ?? "") + (data.content ?? "") }
                  : m
              )
            );
            break;

          case "tool_start":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aid
                  ? {
                      ...m,
                      toolCalls: [
                        ...(m.toolCalls ?? []),
                        { name: data.tool ?? "", status: "running" },
                      ],
                    }
                  : m
              )
            );
            break;

          case "tool_end":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aid
                  ? {
                      ...m,
                      toolCalls: (m.toolCalls ?? []).map((tc) =>
                        tc.name === data.tool && tc.status === "running"
                          ? { ...tc, status: "done", result: data.result }
                          : tc
                      ),
                    }
                  : m
              )
            );
            break;

          case "done":
            if (data.conversation_id) {
              setConversationId(data.conversation_id);
            }
            setMessages((prev) =>
              prev.map((m) => (m.id === aid ? { ...m, streaming: false } : m))
            );
            setIsLoading(false);
            ws.close();
            break;

          case "error":
            setError(data.message ?? "Erreur inconnue");
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aid
                  ? {
                      ...m,
                      content: m.content || `❌ Erreur: ${data.message}`,
                      streaming: false,
                    }
                  : m
              )
            );
            setIsLoading(false);
            ws.close();
            break;
        }
      };

      ws.onerror = () => {
        setError("Connexion WebSocket perdue");
        setIsLoading(false);
      };

      ws.onclose = () => {
        setIsLoading(false);
      };
    },
    [token, conversationId, isLoading]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    wsRef.current?.close();
  }, []);

  // Nettoyer le WebSocket au démontage
  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return { messages, isLoading, error, sendMessage, clearChat, conversationId };
}
