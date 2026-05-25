import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { MessageRow } from "./types";

const POLL_INTERVAL_MS = 5000;

export default function App(): JSX.Element {
  const [address, setAddress] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const cursorRef = useRef<string | null>(null);

  const acquireAddress = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessages([]);
    setSelectedId(null);
    cursorRef.current = null;
    try {
      const res = await api.createAddress();
      setAddress(res.address);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!address) {
      void acquireAddress();
    }
  }, [address, acquireAddress]);

  useEffect(() => {
    if (!address) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const res = await api.listMessages(address, cursorRef.current ?? undefined);
        if (cancelled) return;
        if (res.items.length > 0) {
          setMessages((prev) => [...prev, ...res.items]);
          cursorRef.current = res.next_after;
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
    };

    void poll(); // immediate fetch
    const timer = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [address]);

  const onCopy = async () => {
    if (!address) return;
    await navigator.clipboard.writeText(address);
  };

  const selected = messages.find((m) => m.id === selectedId);

  return (
    <div className="app">
      <header className="hero">
        <h1>TempSES</h1>
        <p className="muted">일회용 이메일 — 새로고침 없이 자동 수신</p>
      </header>

      <section aria-label="임시 주소" className="addr-bar">
        {address ? (
          <>
            <code data-testid="current-address" className="addr">
              {address}
            </code>
            <button onClick={onCopy} aria-label="주소 복사" className="btn-secondary">
              복사
            </button>
            <button
              onClick={acquireAddress}
              aria-label="새 주소 발급"
              className="btn-primary"
              disabled={busy}
            >
              새 주소
            </button>
          </>
        ) : (
          <span className="muted">주소 발급 중…</span>
        )}
      </section>

      {error && <div className="error">{error}</div>}

      <main className="layout">
        <aside aria-label="받은 편지함" className="inbox">
          <h2>받은 편지함 ({messages.length})</h2>
          {messages.length === 0 ? (
            <p className="muted">메일 대기 중…</p>
          ) : (
            <ul>
              {messages.map((m) => (
                <li
                  key={m.id}
                  className={selectedId === m.id ? "selected" : ""}
                  onClick={() => setSelectedId(m.id)}
                >
                  <div className="from">{m.from}</div>
                  <div className="subject">{m.subject || "(제목 없음)"}</div>
                  <div className="muted small">{formatTime(m.received_at)}</div>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section aria-label="메일 본문" className="view">
          {selected ? (
            <MessageView msg={selected} />
          ) : (
            <p className="muted">왼쪽 목록에서 메일을 선택하세요.</p>
          )}
        </section>
      </main>
    </div>
  );
}

function MessageView({ msg }: { msg: MessageRow }): JSX.Element {
  // Defense in depth: sanitized server-side, additionally rendered in a
  // sandboxed iframe with strict CSP and no-referrer.
  const html = msg.body_html_safe;
  const srcdoc =
    `<!doctype html><html><head>` +
    `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'">` +
    `<meta name="referrer" content="no-referrer">` +
    `<style>body{font-family:system-ui;line-height:1.5;color:#111;margin:1rem;}</style>` +
    `</head><body>${html || `<pre>${escapeHtml(msg.body_text)}</pre>`}</body></html>`;

  return (
    <article className="msg">
      <header>
        <h3>{msg.subject || "(제목 없음)"}</h3>
        <p className="muted small">
          From <strong>{msg.from}</strong> · {formatTime(msg.received_at)}
        </p>
      </header>
      <iframe
        title="message body"
        sandbox=""
        referrerPolicy="no-referrer"
        srcDoc={srcdoc}
        data-testid="message-iframe"
      />
      {msg.attachments.length > 0 && (
        <footer>
          <h4>첨부 ({msg.attachments.length})</h4>
          <ul>
            {msg.attachments.map((a) => (
              <li key={a.aid}>
                {a.filename} <span className="muted small">{a.size}B</span>
              </li>
            ))}
          </ul>
        </footer>
      )}
    </article>
  );
}

function formatTime(epoch: number): string {
  if (!epoch) return "";
  const d = new Date(epoch * 1000);
  return d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
