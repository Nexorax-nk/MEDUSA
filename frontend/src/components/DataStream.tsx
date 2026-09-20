import React, { useRef, useState, useEffect } from "react";
import './DataStream.css';

interface DataStreamEntry {
  timestamp?: string;
  text: string;
  type?: "info" | "warning" | "error" | "success" | "action" | "system" | "critical";
}

interface DataStreamProps extends React.HTMLAttributes<HTMLDivElement> {
  entries: DataStreamEntry[];
  title?: string;
  maxVisible?: number;
  streaming?: boolean;
}

const typeColor: Record<string, string> = {
  info: "var(--text-dim)",
  warning: "#f59e0b",
  error: "var(--status-critical)",
  success: "var(--status-success)",
  action: "var(--accent-orange)",
  system: "var(--status-active)",
  critical: "var(--status-critical)",
};

const typeDot: Record<string, string> = {
  info: "var(--text-dim)",
  warning: "#f59e0b",
  error: "var(--status-critical)",
  success: "var(--status-success)",
  action: "var(--accent-orange)",
  system: "var(--status-active)",
  critical: "var(--status-critical)",
};

export function DataStream({
  entries,
  title = "DATA STREAM",
  maxVisible = 8,
  streaming = true,
  className = "",
  ...props
}: DataStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const entriesRef = useRef(entries);
  entriesRef.current = entries;

  useEffect(() => {
    setVisibleCount(0);
    let count = 0;
    const interval = setInterval(() => {
      count++;
      if (count > entriesRef.current.length) {
        clearInterval(interval);
        return;
      }
      setVisibleCount(count);
    }, 150); // Faster reveal for the demo
    return () => clearInterval(interval);
  }, [entries.length]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleCount]);

  return (
    <div
      className={`data-stream-container glass-panel ${className}`}
      {...props}
    >
      <div className="ds-scanline" />

      <div className="ds-header">
        {streaming && <div className="ds-pulse" />}
        <span className="ds-title">{title}</span>
        <span className="ds-count">
          {visibleCount}/{entries.length}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="ds-entries"
        style={{ maxHeight: maxVisible * 28 }}
      >
        {entries.slice(0, visibleCount).map((entry, i) => {
          const type = entry.type ?? "info";
          return (
            <div key={i} className="ds-entry" style={{ animation: "dataStreamFadeIn 0.3s ease-out" }}>
              <div className="ds-dot" style={{ backgroundColor: typeDot[type] }} />
              {entry.timestamp && (
                <span className="ds-time">{entry.timestamp}</span>
              )}
              <span className="ds-text" style={{ color: typeColor[type] }}>{entry.text}</span>
            </div>
          );
        })}
      </div>

      <div className="ds-corner ds-tl" />
      <div className="ds-corner ds-tr" />
      <div className="ds-corner ds-bl" />
      <div className="ds-corner ds-br" />
    </div>
  );
}
