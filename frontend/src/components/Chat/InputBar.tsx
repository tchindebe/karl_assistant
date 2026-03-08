import { useState, useRef, KeyboardEvent } from "react";
import { Send } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function InputBar({ onSend, disabled }: Props) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
    }
  };

  return (
    <div
      className="px-4 py-4 shrink-0"
      style={{ borderTop: "1px solid var(--border)" }}
    >
      <div
        className="flex items-end gap-3 rounded-2xl px-4 py-3"
        style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={
            disabled
              ? "Karl réfléchit..."
              : "Parlez à Karl... (Entrée pour envoyer, Maj+Entrée pour nouvelle ligne)"
          }
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-sm resize-none outline-none text-white placeholder-gray-500"
          style={{ maxHeight: "200px", lineHeight: "1.5" }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="p-2 rounded-xl shrink-0 transition-all"
          style={{
            background:
              disabled || !input.trim() ? "var(--surface2)" : "var(--accent)",
            color: disabled || !input.trim() ? "var(--text-muted)" : "white",
            cursor: disabled || !input.trim() ? "not-allowed" : "pointer",
          }}
        >
          <Send size={16} />
        </button>
      </div>
      <p className="text-center text-xs mt-2" style={{ color: "var(--text-muted)" }}>
        Karl peut se tromper. Vérifiez les opérations critiques.
      </p>
    </div>
  );
}
