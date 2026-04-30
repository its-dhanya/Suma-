import React, { useState } from "react";

function Spinner() {
  return (
    <div
      className="inline-block rounded-full border-4 border-gray-200 border-t-blue-600"
      style={{ width: 18, height: 18, animation: "spin 0.7s linear infinite" }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function formatTime(s) {
  const m = Math.floor(s / 60);
  const sec = String(Math.floor(s % 60)).padStart(2, "0");
  return `${m}:${sec}`;
}

export default function TranscriptView({ transcript }) {
  const [alignment, setAlignment] = useState(null);
  const [loadingAV, setLoadingAV] = useState(false);
  const [avError, setAvError] = useState("");

  const fetchAlignment = async () => {
    setLoadingAV(true);
    setAvError("");
    setAlignment(null);
    try {
      const res = await fetch("http://localhost:8000/av-alignment");
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "AV alignment failed");
      setAlignment(data.alignment);
    } catch (e) {
      setAvError(e.message);
    } finally {
      setLoadingAV(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Plain transcript */}
      {transcript && (
        <div
          className="mt-2 bg-white p-6 rounded-lg shadow-xl border border-gray-300 w-full"
          style={{ fontFamily: "'Lato', sans-serif" }}
        >
          <h2 className="text-2xl font-bold mb-4 border-b pb-2" style={{ color: "#34495E" }}>
            Transcript
          </h2>
          <div className="max-h-96 overflow-y-auto w-full">
            <div
              className="text-base whitespace-pre-wrap w-full"
              style={{ color: "#2C3E50", wordBreak: "break-word" }}
            >
              {transcript}
            </div>
          </div>
        </div>
      )}

      {/* AV Alignment section */}
      <div className="bg-white p-6 rounded-lg shadow-xl border border-gray-300">
        <div className="flex items-center justify-between mb-4 border-b pb-2">
          <h2 className="text-2xl font-bold" style={{ color: "#34495E" }}>
            Audio-Visual Alignment
          </h2>
          <button
            onClick={fetchAlignment}
            disabled={loadingAV}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm transition duration-300 ${
              loadingAV
                ? "bg-blue-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {loadingAV && <Spinner />}
            {loadingAV ? "Aligning…" : "Generate AV Alignment"}
          </button>
        </div>

        <p className="text-sm text-gray-500 mb-4">
          Maps each captured board screenshot to the speech segments spoken while it was on screen.
          Run <strong>Transcribe Audio</strong> first.
        </p>

        {avError && (
          <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded px-4 py-2">
            {avError}
          </p>
        )}

        {alignment && (
          <div className="space-y-3 max-h-[32rem] overflow-y-auto pr-1">
            {alignment.map((entry, i) => (
              <div
                key={i}
                className="border border-gray-200 rounded-lg p-4 bg-gray-50 hover:shadow-md transition"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-mono text-xs text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
                    {entry.screenshot}
                  </span>
                  <span className="text-xs text-gray-500 font-semibold">
                    @ {formatTime(entry.capture_time_s)}
                  </span>
                </div>
                {entry.transcript_segments.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">No speech in this window</p>
                ) : (
                  entry.transcript_segments.map((seg, j) => (
                    <div key={j} className="flex gap-2 text-sm text-gray-700 mb-1">
                      <span className="font-mono text-xs text-gray-400 shrink-0 mt-0.5">
                        {formatTime(seg.start)}–{formatTime(seg.end)}
                      </span>
                      <span>{seg.text}</span>
                    </div>
                  ))
                )}
              </div>
            ))}
          </div>
        )}

        {!alignment && !avError && !loadingAV && (
          <p className="text-sm text-gray-400 italic text-center py-6">
            Click "Generate AV Alignment" to see board screenshots matched with spoken content.
          </p>
        )}
      </div>
    </div>
  );
}