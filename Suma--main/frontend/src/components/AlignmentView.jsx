import React, { useState } from "react";

function Spinner() {
  return (
    <div
      style={{
        display: "inline-block",
        width: 18, height: 18,
        border: "3px solid #f3f4f6",
        borderTop: "3px solid #e74c3c",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function formatTime(s) {
  const m   = Math.floor(s / 60);
  const sec = String(Math.floor(s % 60)).padStart(2, "0");
  return `${m}:${sec}`;
}

export default function AlignmentView({ sessionFolder }) {
  const [alignmentData, setAlignmentData] = useState(null);
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState(null);

  const fetchAlignment = async () => {
    setLoading(true);
    setError(null);
    try {
      const res  = await fetch("http://localhost:8000/av-alignment");
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch alignment");
      setAlignmentData(data.alignment);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="bg-gradient-to-r from-red-700 to-rose-800 rounded-xl p-5 text-white shadow">
        <h2 className="text-xl font-extrabold mb-1">🎬 Audio-Visual Alignment</h2>
        <p className="text-red-100 text-sm">
          Each captured board image is matched with what was spoken at that moment,
          and the OCR text extracted from the board.
        </p>
      </div>

      <div className="flex justify-center">
        <button
          onClick={fetchAlignment}
          disabled={loading}
          className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold shadow-lg transition duration-300 ${
            loading
              ? "bg-red-200 text-gray-500 cursor-not-allowed"
              : "bg-red-600 text-white hover:bg-red-700 active:scale-95"
          }`}
        >
          {loading ? <><Spinner /> Syncing…</> : "Get Audio-Visual Alignment"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 p-4 rounded-lg text-sm font-semibold text-center">
          ⚠ {error}
        </div>
      )}

      {!alignmentData && !error && !loading && (
        <p className="text-center text-gray-400 italic text-sm py-6">
          Click the button above to see which board images align with which spoken words.
        </p>
      )}

      {alignmentData && alignmentData.length === 0 && (
        <div className="text-center text-gray-500 italic mt-6 text-sm">
          No alignment data found. Make sure you have transcribed the audio and captured images.
        </div>
      )}

      {alignmentData && alignmentData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-2">
          {alignmentData.map((item, index) => (
            <div
              key={index}
              className="bg-white border border-gray-200 rounded-2xl shadow-md overflow-hidden hover:shadow-xl transition-shadow"
            >
              {/* Card header */}
              <div className="bg-gradient-to-r from-gray-700 to-gray-900 text-white px-4 py-2 flex items-center justify-between">
                <span className="font-mono text-xs truncate">{item.screenshot}</span>
                <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full shrink-0 ml-2">
                  @{formatTime(item.capture_time_s)}
                </span>
              </div>

              {/* Board image */}
              <div className="bg-gray-50 flex items-center justify-center p-2">
                <img
                  src={`http://localhost:8000/sessions/${sessionFolder}/${item.screenshot}`}
                  alt={item.screenshot}
                  className="max-h-52 object-contain rounded border border-gray-200 w-full"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="140"><rect width="100%" height="100%" fill="%23f9fafb"/><text x="50%" y="50%" font-family="sans-serif" font-size="13" fill="%239ca3af" text-anchor="middle" dy=".3em">Image unavailable</text></svg>`;
                  }}
                />
              </div>

              <div className="p-4 space-y-3">
                {/* OCR text from board */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-green-700 mb-1 flex items-center gap-1">
                    📷 Board OCR Text
                  </h4>
                  {item.ocr_text && item.ocr_text.trim() ? (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-xs text-gray-800 font-mono whitespace-pre-wrap">
                      {item.ocr_text}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 italic">No text extracted from board image.</p>
                  )}
                </div>

                {/* Spoken words */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-blue-700 mb-1 flex items-center gap-1">
                    🎙 Spoken During This Frame
                  </h4>
                  {item.transcript_segments && item.transcript_segments.length > 0 ? (
                    <ul className="space-y-1.5">
                      {item.transcript_segments.map((seg, i) => (
                        <li key={i} className="flex gap-2 bg-blue-50 border-l-4 border-blue-400 p-2 rounded text-sm text-gray-800">
                          <span className="font-mono text-xs text-blue-500 shrink-0 mt-0.5">
                            [{seg.start.toFixed(1)}s–{seg.end.toFixed(1)}s]
                          </span>
                          <span>{seg.text}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-gray-400 italic">No speech detected during this timeframe.</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
