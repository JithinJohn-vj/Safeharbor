"use client";

import { useState, useEffect, useLayoutEffect, useRef, useCallback } from "react";

const COUNTRIES = [
  {
    code: "SE",
    name: "Sweden",
    exclusion:
      "Spelpaus (spelpaus.se) — Sweden's national self-exclusion register. Free, instant, covers all licensed Swedish operators.",
    helpline: "Stödlinjen: 020-819 100 (free, 24/7)",
  },
  {
    code: "GB",
    name: "United Kingdom",
    exclusion:
      "GamStop (gamstop.co.uk) — covers all UK Gambling Commission licensed sites. Free and effective within 24 hours.",
    helpline: "GamCare: 0808 8020 133 (free, 24/7)",
  },
  {
    code: "US",
    name: "United States",
    exclusion:
      "State-run self-exclusion programs — each state has its own register. NCSL.org has links for every state.",
    helpline: "NCPG Helpline: 1-800-522-4700 (24/7)",
  },
  {
    code: "AU",
    name: "Australia",
    exclusion:
      "BetStop (betstop.com.au) — national register launched 2023, covers all Australian licensed operators.",
    helpline: "Gambling Helpline: 1800 858 858 (free, 24/7)",
  },
  {
    code: "DE",
    name: "Germany",
    exclusion:
      "OASIS — national cross-provider exclusion database, mandatory for all licensed operators since 2021.",
    helpline: "Bundeszentrale: 0800 040 040 (free)",
  },
  {
    code: "IE",
    name: "Ireland",
    exclusion:
      "Self-exclusion available through individual operators; national register in development.",
    helpline: "Gambling Care: 1800 936 725",
  },
  {
    code: "OTHER",
    name: "Other country",
    exclusion:
      "Most licensed jurisdictions have self-exclusion programs. I can help you find the one for your country.",
    helpline: "Gamblers Anonymous: ga.org (worldwide chapters)",
  },
];

const QUICK_ACTIONS = [
  "How do I self-exclude from gambling sites?",
  "I'm drowning in debt from gambling",
  "I want to stop but keep relapsing",
  "My family found out and I don't know what to do",
];

/** Nine distress signals — any match surfaces crisis helplines immediately */
const CRISIS_SIGNALS = [
  "suicide",
  "kill myself",
  "end it all",
  "can't go on",
  "want to die",
  "no point living",
  "harm myself",
  "ending my life",
  "better off dead",
];

function detectCrisis(text) {
  const lower = text.toLowerCase();
  return CRISIS_SIGNALS.some((w) => lower.includes(w));
}

const PROBE_USER =
  "(You've been quiet for about a minute. As SafeHarbor, send one brief warm check-in — gentle presence only, no assumptions. One short paragraph.)";

const SESSION_STORAGE_KEY = "safeharbor_session_id";

/** Local dev: default so chat works if .env was not copied or Next was not restarted after adding NEXT_PUBLIC_DJANGO_API_URL */
function getDjangoApiBase() {
  const fromEnv = (process.env.NEXT_PUBLIC_DJANGO_API_URL || "").trim().replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (process.env.NODE_ENV === "development") return "http://127.0.0.1:8000";
  return "";
}

function connectionErrorMessage(err) {
  const msg = err instanceof Error ? err.message : String(err);
  const network =
    err instanceof TypeError ||
    (typeof msg === "string" && (msg.includes("Failed to fetch") || msg.includes("NetworkError")));
  if (network) {
    return (
      "I'm having trouble reaching the server. Start Django: cd backend && . .venv/bin/activate && " +
      "python manage.py runserver 0.0.0.0:8000 — then reload this page. " +
      "If it still fails, add NEXT_PUBLIC_DJANGO_API_URL=http://127.0.0.1:8000 to .env in the project root and restart npm run dev."
    );
  }
  return `I'm having trouble connecting right now. (${msg})`;
}

function buildSystemPrompt(name, country) {
  return `You are SafeHarbor, a compassionate and expert gambling addiction consultant. You are speaking with ${name} from ${country.name}.

Your role combines three things:
1. EMOTIONAL SUPPORT — Non-judgmental counseling using motivational interviewing. Meet people where they are. Validate before advising. Ask one thoughtful question at a time. Never shame or lecture.

2. LEGAL & PRACTICAL GUIDANCE for ${country.name}:
   - Self-exclusion: ${country.exclusion}
   - Gambling debts: Debts to unlicensed operators may be legally unenforceable. Licensed operators must offer responsible gambling tools. Debt collectors must follow fair collection laws. Debt consolidation and financial counseling are options.
   - Consumer protections: Regulators can investigate operators who ignored self-exclusion or addiction signals. Document everything.
   - Crisis helpline: ${country.helpline}

3. RECOVERY RESOURCES — Gamblers Anonymous (ga.org), professional therapists specializing in behavioral addiction, financial counselors, family support groups (Gam-Anon).

RESPONSE STYLE:
- Warm, human, never clinical
- Keep responses to 2–3 short paragraphs maximum
- Be specific with legal/financial info when asked
- Always end with a gentle open question unless the person is in crisis

CRISIS PROTOCOL: If the person expresses suicidal thoughts, self-harm, or severe hopelessness — acknowledge their pain with full presence, immediately share the crisis helpline (${country.helpline}) and emergency services (112/999/911), and gently encourage them to reach out right now. Stay present with them.

PROACTIVE CHECK-IN: If the conversation has been quiet and you're checking in, be brief and warm — just ask how they're doing, no pressure.

Remember: You are often the first person someone has told about their gambling. That trust is everything.`;
}

function AnchorIcon({ size = 20 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="12" cy="5" r="3" />
      <line x1="12" y1="8" x2="12" y2="21" />
      <path d="M5 13H2a10 10 0 0 0 20 0h-3" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

export default function SafeHarbor() {
  const [phase, setPhase] = useState("onboard");
  const [name, setName] = useState("");
  const [country, setCountry] = useState(COUNTRIES[0]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [proactivePending, setProactivePending] = useState(false);
  const [crisisMode, setCrisisMode] = useState(false);
  const [sessionId, setSessionId] = useState("");

  const messagesScrollRef = useRef(null);
  const nudgeTimerRef = useRef(null);
  const inputRef = useRef(null);
  const sessionIdRef = useRef("");
  const messagesRef = useRef(messages);
  const loadingRef = useRef(loading);
  const nameRef = useRef(name);
  const countryRef = useRef(country);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);
  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);
  useEffect(() => {
    nameRef.current = name;
  }, [name]);
  useEffect(() => {
    countryRef.current = country;
  }, [country]);
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  /** Restore prior session from Django (persistent memory across visits). */
  useEffect(() => {
    const base = getDjangoApiBase();
    if (!base || typeof window === "undefined") return;
    const sid = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!sid) return;
    let cancelled = false;
    fetch(`${base}/api/session/${sid}/`)
      .then((r) => {
        if (r.status === 404 && typeof window !== "undefined") {
          localStorage.removeItem(SESSION_STORAGE_KEY);
        }
        return r.ok ? r.json() : null;
      })
      .then((data) => {
        if (cancelled || !data?.messages?.length) return;
        sessionIdRef.current = sid;
        setSessionId(sid);
        if (data.display_name) setName(data.display_name);
        if (data.country_code) {
          const c = COUNTRIES.find((x) => x.code === data.country_code);
          if (c) setCountry(c);
        }
        setMessages(
          data.messages.map((m) => ({
            role: m.role,
            content: m.content,
          }))
        );
        setPhase("chat");
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  /** Keep the latest messages in view: scroll the chat pane (not the whole page). */
  const scrollChatToBottom = useCallback(() => {
    const el = messagesScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, []);

  useLayoutEffect(() => {
    scrollChatToBottom();
  }, [messages, loading, proactivePending, scrollChatToBottom]);

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      requestAnimationFrame(scrollChatToBottom);
    });
    return () => cancelAnimationFrame(id);
  }, [messages, loading, proactivePending, scrollChatToBottom]);

  const callClaude = useCallback(async (msgs) => {
    const base = getDjangoApiBase();
    if (!base) {
      throw new Error(
        "Set NEXT_PUBLIC_DJANGO_API_URL in .env to your Django server URL (required in production builds)."
      );
    }
    const res = await fetch(`${base}/api/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionIdRef.current || undefined,
        display_name: nameRef.current,
        country_code: countryRef.current.code,
        system: buildSystemPrompt(nameRef.current, countryRef.current),
        messages: msgs.map((m) => ({ role: m.role, content: m.content })),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || res.statusText);
    }
    if (data.session_id) {
      sessionIdRef.current = data.session_id;
      setSessionId(data.session_id);
      if (typeof window !== "undefined") {
        localStorage.setItem(SESSION_STORAGE_KEY, data.session_id);
      }
    }
    return data.text || "I'm here for you. Tell me more.";
  }, []);

  const runProactiveCheckIn = useCallback(async () => {
    if (loadingRef.current) return;
    const hist = messagesRef.current;
    if (hist.length === 0) return;

    const probe = { role: "user", content: PROBE_USER };
    const forApi = [...hist, probe];
    setProactivePending(true);
    setLoading(true);
    try {
      const reply = await callClaude(forApi);
      if (detectCrisis(reply)) setCrisisMode(true);
      setMessages([...hist, { role: "assistant", content: reply, proactive: true }]);
    } catch (e) {
      setMessages([
        ...hist,
        {
          role: "assistant",
          content: connectionErrorMessage(e),
          proactive: true,
        },
      ]);
    } finally {
      setLoading(false);
      setProactivePending(false);
      if (nudgeTimerRef.current) clearTimeout(nudgeTimerRef.current);
      nudgeTimerRef.current = setTimeout(() => {
        runProactiveCheckIn();
      }, 60000);
    }
  }, [callClaude]);

  const resetNudgeTimer = useCallback(() => {
    if (nudgeTimerRef.current) clearTimeout(nudgeTimerRef.current);
    nudgeTimerRef.current = setTimeout(() => {
      runProactiveCheckIn();
    }, 60000);
  }, [runProactiveCheckIn]);

  useEffect(() => {
    if (phase === "chat") {
      resetNudgeTimer();
      const t = setTimeout(() => inputRef.current?.focus(), 100);
      return () => {
        clearTimeout(t);
        if (nudgeTimerRef.current) clearTimeout(nudgeTimerRef.current);
      };
    }
    return () => {
      if (nudgeTimerRef.current) clearTimeout(nudgeTimerRef.current);
    };
  }, [phase, resetNudgeTimer]);

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    if (nudgeTimerRef.current) clearTimeout(nudgeTimerRef.current);

    if (detectCrisis(text)) setCrisisMode(true);

    const userMsg = { role: "user", content: text };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setLoading(true);
    try {
      const reply = await callClaude(history);
      if (detectCrisis(reply)) setCrisisMode(true);
      setMessages([...history, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages([
        ...history,
        {
          role: "assistant",
          content: connectionErrorMessage(e),
        },
      ]);
    } finally {
      setLoading(false);
      resetNudgeTimer();
    }
  };

  const startSession = async () => {
    if (!name.trim()) return;
    if (typeof window !== "undefined" && !sessionIdRef.current) {
      const existing = localStorage.getItem(SESSION_STORAGE_KEY);
      if (existing) {
        sessionIdRef.current = existing;
        setSessionId(existing);
      } else {
        const sid = crypto.randomUUID();
        sessionIdRef.current = sid;
        setSessionId(sid);
        localStorage.setItem(SESSION_STORAGE_KEY, sid);
      }
    }
    setPhase("chat");
    setLoading(true);
    const opening = [
      {
        role: "user",
        content: `Hi, my name is ${name}. I'm from ${country.name} and I'm struggling with gambling addiction. I wanted to reach out for help.`,
      },
    ];
    try {
      const reply = await callClaude(opening);
      if (detectCrisis(reply)) setCrisisMode(true);
      setMessages([...opening, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages([
        ...opening,
        {
          role: "assistant",
          content: connectionErrorMessage(e),
        },
      ]);
    } finally {
      setLoading(false);
      resetNudgeTimer();
    }
  };

  if (phase === "onboard") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center mx-auto mb-4">
              <AnchorIcon size={28} />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">SafeHarbor</h1>
            <p className="text-gray-500 text-sm leading-relaxed max-w-sm mx-auto">
              A confidential space for gambling addiction support — emotional, legal, and financial
              guidance, all in one place.
            </p>
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <div className="mb-5">
              <label htmlFor="safeharbor-name" className="block text-sm font-medium text-gray-700 mb-2">
                Your first name
              </label>
              <input
                id="safeharbor-name"
                type="text"
                className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                placeholder="What should I call you?"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && startSession()}
                autoComplete="given-name"
              />
            </div>

            <div className="mb-6">
              <label htmlFor="safeharbor-country" className="block text-sm font-medium text-gray-700 mb-2">
                Your country
              </label>
              <select
                id="safeharbor-country"
                className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                value={country.code}
                onChange={(e) => setCountry(COUNTRIES.find((c) => c.code === e.target.value))}
              >
                {COUNTRIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-400 mt-2">
                Used to provide country-specific legal and self-exclusion guidance.
              </p>
            </div>

            <button
              type="button"
              onClick={startSession}
              disabled={!name.trim()}
              className={`w-full py-3 rounded-xl text-sm font-medium transition-all ${
                name.trim()
                  ? "bg-teal-600 text-white hover:bg-teal-700 active:scale-[0.98]"
                  : "bg-gray-100 text-gray-400 cursor-not-allowed"
              }`}
            >
              Start confidential session
            </button>

            <p className="text-center text-xs text-gray-400 mt-4">
              Everything shared here is private, non-judgmental, and free.
            </p>
          </div>

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3 text-center">
            {[
              ["Emotional support", "Counseling & recovery guidance"],
              ["Legal guidance", "Self-exclusion & debt rights"],
              ["Proactive care", "Check-ins & crisis support"],
            ].map(([t, d]) => (
              <div key={t} className="bg-white rounded-xl border border-gray-100 p-3">
                <p className="text-xs font-medium text-teal-700 mb-1">{t}</p>
                <p className="text-xs text-gray-400 leading-snug">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const helplineParts = country.helpline.split(": ");
  const helplineLabel = helplineParts[0];
  const helplineNumber = helplineParts.slice(1).join(": ");

  return (
    <div className="h-[100dvh] max-h-[100dvh] flex flex-col overflow-hidden bg-gray-50 max-w-lg mx-auto w-full shadow-xl border-x border-gray-100">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3 flex-shrink-0">
        <div className="w-9 h-9 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center flex-shrink-0">
          <AnchorIcon size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900">SafeHarbor</p>
          <p className="text-xs text-teal-600 truncate">Confidential session · {country.name}</p>
        </div>
        <div className="text-right flex-shrink-0 hidden sm:block">
          <p className="text-xs text-gray-500 truncate max-w-[140px]">{helplineLabel}</p>
          <p className="text-xs font-medium text-gray-700 truncate max-w-[140px]">{helplineNumber}</p>
        </div>
      </header>

      {crisisMode && (
        <div
          className="mx-3 mt-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex-shrink-0"
          role="alert"
        >
          <p className="text-xs font-semibold text-red-700 mb-1">
            You&apos;re not alone — crisis support available now
          </p>
          <p className="text-xs text-red-600">
            {country.helpline} · Emergency: 112 / 999 / 911
          </p>
        </div>
      )}

      {proactivePending && (
        <div className="mx-3 mt-2 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center gap-3 flex-shrink-0">
          <BellIcon />
          <p className="text-xs text-amber-800 flex-1">SafeHarbor is checking in…</p>
        </div>
      )}

      <div
        ref={messagesScrollRef}
        className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-4 py-4 space-y-4 scroll-smooth"
      >
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center flex-shrink-0 mt-1">
                <AnchorIcon size={12} />
              </div>
            )}
            <div className="max-w-[78%]">
              {msg.proactive && (
                <p className="text-[10px] uppercase tracking-wide text-amber-700 font-medium mb-1 px-1">
                  Gentle check-in
                </p>
              )}
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words ${
                  msg.role === "user"
                    ? "bg-teal-600 text-white rounded-br-sm"
                    : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"
                }`}
              >
                {msg.content}
              </div>
            </div>
          </div>
        ))}

        {loading && !proactivePending && (
          <div className="flex gap-2 justify-start">
            <div className="w-7 h-7 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center flex-shrink-0 mt-1">
              <AnchorIcon size={12} />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1 items-center h-4">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-2 h-2 rounded-full bg-teal-400 safeharbor-dot"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.length <= 2 && !loading && (
          <div className="pt-2">
            <p className="text-xs text-gray-400 mb-3 text-center">Common topics to start with:</p>
            <div className="grid grid-cols-1 gap-2">
              {QUICK_ACTIONS.map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => sendMessage(a)}
                  className="text-left px-4 py-2.5 rounded-xl border border-gray-200 bg-white hover:border-teal-300 hover:bg-teal-50 text-xs text-gray-600 hover:text-teal-700 transition-all"
                >
                  {a}
                </button>
              ))}
            </div>
          </div>
        )}

      </div>

      <div className="bg-white border-t border-gray-200 px-4 py-3 flex gap-3 items-end flex-shrink-0 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <textarea
          ref={inputRef}
          rows={1}
          className="flex-1 resize-none px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent max-h-[100px]"
          placeholder="What's on your mind?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage(input);
            }
          }}
          disabled={loading}
          aria-label="Message"
        />
        <button
          type="button"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all flex-shrink-0 ${
            input.trim() && !loading
              ? "bg-teal-600 text-white hover:bg-teal-700 active:scale-95"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
          }`}
          aria-label="Send"
        >
          <SendIcon />
        </button>
      </div>
    </div>
  );
}
