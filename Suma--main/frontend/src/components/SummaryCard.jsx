import React, { useState } from "react";

// ── Source badge ───────────────────────────────────────────────────────────────
function SourceBadge({ source }) {
  if (!source) return null;
  const map = {
    audio: { label: "🎙 Audio", cls: "bg-blue-100 text-blue-700 border-blue-300" },
    board: { label: "📷 Board", cls: "bg-green-100 text-green-700 border-green-300" },
    both:  { label: "🎙📷 Both",  cls: "bg-purple-100 text-purple-700 border-purple-300" },
  };
  const key = source.toLowerCase().replace(/[^a-z]/g, "");
  const config = map[key] || map[source] || { label: source, cls: "bg-gray-100 text-gray-600 border-gray-300" };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border shrink-0 ${config.cls}`}>
      {config.label}
    </span>
  );
}

// ── Section wrapper ────────────────────────────────────────────────────────────
function Section({ title, icon, color, children }) {
  const [open, setOpen] = useState(true);
  const colors = {
    indigo: "from-indigo-600 to-indigo-800 border-indigo-300",
    blue:   "from-blue-600 to-blue-800 border-blue-300",
    green:  "from-green-600 to-green-800 border-green-300",
    purple: "from-purple-600 to-purple-800 border-purple-300",
    amber:  "from-amber-500 to-amber-700 border-amber-300",
    red:    "from-red-600 to-red-800 border-red-300",
    teal:   "from-teal-600 to-teal-800 border-teal-300",
    gray:   "from-gray-600 to-gray-800 border-gray-300",
  };
  return (
    <div className={`rounded-xl border overflow-hidden shadow-sm mb-5 ${colors[color]?.split(" ").slice(2).join(" ") || "border-gray-300"}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className={`w-full flex items-center justify-between px-5 py-3 bg-gradient-to-r text-white font-bold text-lg ${colors[color]?.split(" ").slice(0, 2).join(" ") || "from-gray-600 to-gray-800"}`}
      >
        <span>{icon} {title}</span>
        <span className="text-sm opacity-70">{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="p-5 bg-white">{children}</div>}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function SummaryCard({ summary }) {
  if (!summary) return null;

  // Error / raw fallback
  if (summary.error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <strong>Summarization error:</strong> {summary.error}
      </div>
    );
  }
  if (summary.raw_response) {
    return (
      <div className="p-6 bg-white border border-gray-300 rounded-xl shadow">
        <h2 className="text-xl font-bold text-gray-700 mb-3">Raw Response (JSON parse failed)</h2>
        <pre className="text-xs text-gray-600 bg-gray-50 p-4 rounded overflow-x-auto whitespace-pre-wrap">{summary.raw_response}</pre>
      </div>
    );
  }

  const toArr = v => Array.isArray(v) ? v : v != null ? [v] : [];

  const {
    title, overview, summary: finalSummary,
    core_concepts,
    board_content_summary, audio_content_summary,
    key_points, examples, applications, questions,
    // legacy fields
    detailed_explanation, takeaways, resources,
  } = summary;

  return (
    <div className="space-y-1 font-sans">

      {/* ── Title + overview ── */}
      {(title || overview) && (
        <div className="bg-gradient-to-br from-indigo-700 to-blue-800 rounded-2xl p-6 text-white shadow-lg mb-5">
          {title && <h2 className="text-2xl font-extrabold mb-2">{title}</h2>}
          {overview && <p className="text-indigo-100 leading-relaxed">{overview}</p>}
        </div>
      )}

      {/* ── Audio vs Board split ── */}
      {(audio_content_summary || board_content_summary) && (
        <div className="grid md:grid-cols-2 gap-4 mb-5">
          {audio_content_summary && (
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 shadow-sm">
              <h3 className="font-bold text-blue-800 mb-2 flex items-center gap-2">
                <span className="text-xl">🎙</span> Audio Summary
                <span className="text-xs bg-blue-100 text-blue-600 border border-blue-300 px-2 py-0.5 rounded-full">from microphone</span>
              </h3>
              <p className="text-blue-900 text-sm leading-relaxed">{audio_content_summary}</p>
            </div>
          )}
          {board_content_summary && (
            <div className="rounded-xl border border-green-200 bg-green-50 p-4 shadow-sm">
              <h3 className="font-bold text-green-800 mb-2 flex items-center gap-2">
                <span className="text-xl">📷</span> Board Summary
                <span className="text-xs bg-green-100 text-green-600 border border-green-300 px-2 py-0.5 rounded-full">from OCR images</span>
              </h3>
              <p className="text-green-900 text-sm leading-relaxed">{board_content_summary}</p>
            </div>
          )}
        </div>
      )}

      {/* ── Core Concepts ── */}
      {toArr(core_concepts).length > 0 && (
        <Section title="Core Concepts" icon="💡" color="indigo">
          <div className="space-y-4">
            {toArr(core_concepts).map((c, i) => {
              if (typeof c === "string") return (
                <div key={i} className="flex gap-3 items-start p-3 bg-indigo-50 rounded-lg border border-indigo-100">
                  <span className="font-bold text-indigo-700 shrink-0">#{i + 1}</span>
                  <p className="text-gray-800 text-sm">{c}</p>
                </div>
              );
              return (
                <div key={i} className="p-4 bg-indigo-50 rounded-lg border border-indigo-100">
                  <div className="flex items-start gap-2 flex-wrap mb-1">
                    <span className="font-bold text-indigo-800">{c.name}</span>
                    {c.source && <SourceBadge source={c.source} />}
                  </div>
                  {c.explanation && <p className="text-gray-700 text-sm leading-relaxed">{c.explanation}</p>}
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* ── Key Points ── */}
      {toArr(key_points || takeaways).length > 0 && (
        <Section title="Key Points" icon="📌" color="amber">
          <ul className="space-y-2">
            {toArr(key_points || takeaways).map((p, i) => (
              <li key={i} className="flex items-start gap-2 text-gray-800 text-sm">
                <span className="text-amber-500 font-bold shrink-0 mt-0.5">▸</span>
                <span>{typeof p === "string" ? p : JSON.stringify(p)}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* ── Examples ── */}
      {toArr(examples).length > 0 && (
        <Section title="Examples" icon="🔬" color="green">
          <div className="space-y-3">
            {toArr(examples).map((ex, i) => (
              <div key={i} className="p-3 bg-green-50 rounded-lg border border-green-200 text-sm text-gray-800">
                {typeof ex === "string" ? ex
                  : ex.example ? ex.example
                  : JSON.stringify(ex)}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Detailed explanation (legacy) ── */}
      {detailed_explanation && (
        <Section title="Detailed Explanation" icon="📖" color="blue">
          <p className="text-gray-800 text-sm leading-relaxed">{detailed_explanation}</p>
        </Section>
      )}

      {/* ── Applications ── */}
      {toArr(applications).length > 0 && (
        <Section title="Real-World Applications" icon="🌐" color="teal">
          <ul className="space-y-2">
            {toArr(applications).map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-800">
                <span className="text-teal-600 shrink-0 mt-0.5">●</span>
                <span>{typeof a === "string" ? a : JSON.stringify(a)}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* ── Questions ── */}
      {toArr(questions).length > 0 && (
        <Section title="Possible Exam Questions" icon="❓" color="red">
          <ol className="space-y-3 list-decimal list-inside">
            {toArr(questions).map((q, i) => {
              const text = typeof q === "string" ? q
                : q["possible exam question"] ? q["possible exam question"]
                : q.question ? q.question
                : JSON.stringify(q);
              return (
                <li key={i} className="text-gray-800 text-sm p-3 bg-red-50 rounded-lg border border-red-100">
                  {text}
                </li>
              );
            })}
          </ol>
        </Section>
      )}

      {/* ── Resources (legacy) ── */}
      {toArr(resources).length > 0 && (
        <Section title="Resources" icon="🔗" color="gray">
          <ul className="space-y-2">
            {toArr(resources).map((r, i) => (
              <li key={i} className="text-sm text-gray-800 flex items-start gap-2">
                {r.type && (
                  <span className="shrink-0 text-xs font-bold uppercase bg-indigo-100 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded-full">
                    {r.type}
                  </span>
                )}
                <div>
                  {r.title && <span className="font-semibold text-blue-700">{r.title}</span>}
                  {r.url && (
                    <> — <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-green-700 underline break-all">{r.url}</a></>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* ── Final summary ── */}
      {finalSummary && (
        <div className="bg-gradient-to-r from-gray-800 to-gray-900 rounded-xl p-5 text-white shadow-lg mt-2">
          <h3 className="font-bold text-lg mb-2">📋 Final Recap</h3>
          <p className="text-gray-200 text-sm leading-relaxed">{finalSummary}</p>
        </div>
      )}

    </div>
  );
}