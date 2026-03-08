import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Wrench, ChevronDown, ChevronUp, Brain } from "lucide-react";
import { useState } from "react";
import type { ChatMessage } from "../../hooks/useChat";

interface Props {
  message: ChatMessage;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const [showThinking, setShowThinking] = useState(false);

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-sm font-bold"
        style={{
          background: isUser ? "var(--accent)" : "var(--surface2)",
          color: "white",
        }}
      >
        {isUser ? "U" : "K"}
      </div>

      {/* Bulle */}
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 flex flex-col gap-2 ${
          isUser ? "rounded-tr-sm" : "rounded-tl-sm"
        }`}
        style={{
          background: isUser ? "var(--accent)" : "var(--surface)",
          border: isUser ? "none" : "1px solid var(--border)",
        }}
      >
        {/* Thinking (si présent) */}
        {message.thinking && (
          <div>
            <button
              onClick={() => setShowThinking((v) => !v)}
              className="flex items-center gap-1.5 text-xs mb-1"
              style={{ color: "var(--text-muted)" }}
            >
              <Brain size={12} />
              Réflexion
              {showThinking ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showThinking && (
              <div
                className="text-xs px-3 py-2 rounded-lg italic"
                style={{
                  background: "var(--surface2)",
                  color: "var(--text-muted)",
                  borderLeft: "3px solid var(--accent)",
                  maxHeight: "200px",
                  overflowY: "auto",
                }}
              >
                {message.thinking}
              </div>
            )}
          </div>
        )}

        {/* Appels d'outils */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-1">
            {message.toolCalls.map((tc, i) => (
              <ToolCallBadge key={i} name={tc.name} status={tc.status} result={tc.result} />
            ))}
          </div>
        )}

        {/* Contenu texte */}
        {message.content ? (
          isUser ? (
            <p className="text-sm text-white whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none text-sm">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    const inline = !match;
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus as any}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ borderRadius: "8px", fontSize: "0.8em" }}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )
        ) : message.streaming ? (
          <span className="inline-block w-2 h-4 rounded-sm animate-pulse" style={{ background: "var(--accent)" }} />
        ) : null}
      </div>
    </div>
  );
}

function ToolCallBadge({
  name,
  status,
  result,
}: {
  name: string;
  status: string;
  result?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  const color =
    status === "done"
      ? "var(--green)"
      : status === "error"
      ? "var(--red)"
      : "var(--yellow)";

  const icon = status === "done" ? "✅" : status === "error" ? "❌" : "⏳";

  return (
    <div
      className="flex flex-col gap-1 px-3 py-1.5 rounded-lg text-xs cursor-pointer"
      style={{ background: "var(--surface2)", border: `1px solid ${color}20` }}
      onClick={() => result && setExpanded((v) => !v)}
    >
      <div className="flex items-center gap-2">
        <Wrench size={11} style={{ color }} />
        <span style={{ color }} className="font-medium">
          {icon} {name.replace(/_/g, " ")}
        </span>
        {result && (
          <span style={{ color: "var(--text-muted)" }}>
            {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          </span>
        )}
      </div>
      {expanded && result && (
        <pre
          className="mt-1 text-xs overflow-auto rounded"
          style={{ color: "var(--text-muted)", maxHeight: "100px" }}
        >
          {result}
        </pre>
      )}
    </div>
  );
}
