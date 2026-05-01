import React, { useState } from "react";

function Spinner() {
  return (
    <div
      style={{
        display: "inline-block",
        width: 18, height: 18,
        border: "3px solid #e5e7eb",
        borderTop: "3px solid #2563eb",
        borderRadius: "50%",
        animation: "spin 0.7s linear infinite",
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

export default function TranscriptView({ transcript, sessionFolder }) {
  const [timedSegments, setTimedSegments] = useState(null);
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState("");

  // Fetch the timed segments JSON directly from the backend static files
  const fetchTimedSegments = async () => {
    if (!sessionFolder) {
      setError("No active session found.");
      return;
    }
    setLoading(true);
    setError("");
    setTimedSegments(null);
    try {
      const res  = await fetch(`http://localhost:8000/sessions/${sessionFolder}/transcript_timed.json`);
      if (!res.ok) throw new Error("transcript_timed.json not found. Run transcription first.");
      const data = await res.json();
      setTimedSegments(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const totalDuration = timedSegments?.length
    ? timedSegments[timedSegments.length - 1].end
    : 0;

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="bg-gradient-to-r from-green-700 to-teal-700 rounded-xl p-5 text-white shadow">
        <h2 className="text-xl font-extrabold mb-1">📝 Transcript</h2>
        <p className="text-green-100 text-sm">
          Audio transcript is generated automatically when you stop a session.
          Use the timed view below to see exact timestamps.
        </p>
      </div>

      {/* ── Status banner if no transcript yet ── */}
      {!transcript && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-4 flex items-start gap-3 text-sm text-yellow-800">
          <span className="text-xl">⏳</span>
          <div>
            <strong>Transcription in progress or not yet started.</strong><br />
            After stopping a session, transcription runs automatically in the background.
            This may take a minute depending on audio length.
          </div>
        </div>
      )}

      {/* ── Plain transcript ── */}
      {transcript && (
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <div className="flex items-center justify-between mb-3 border-b pb-2">
            <h3 className="text-lg font-bold text-gray-800">Full Transcript</h3>
            <span className="text-xs bg-green-100 text-green-700 border border-green-300 px-2 py-0.5 rounded-full font-semibold">
              {transcript.split(" ").filter(Boolean).length} words
            </span>
          </div>
          <div className="max-h-80 overflow-y-auto">
            <p className="text-gray-800 text-base leading-relaxed whitespace-pre-wrap">{transcript}</p>
          </div>
        </div>
      )}

      {/* ── Timed segments ── */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <div className="flex items-center justify-between mb-3 border-b pb-2">
          <h3 className="text-lg font-bold text-gray-800">
            🕐 Timed Segments
          </h3>
          <button
            onClick={fetchTimedSegments}
            disabled={loading}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg font-semibold text-sm transition duration-300 ${
              loading
                ? "bg-blue-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700 active:scale-95"
            }`}
          >
            {loading && <Spinner />}
            {loading ? "Loading…" : "Load Timed Segments"}
          </button>
        </div>

        <p className="text-xs text-gray-500 mb-4">
          Each segment shows the exact second range when those words were spoken — used for audio-visual alignment.
        </p>

        {error && (
          <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded px-4 py-2">
            ⚠ {error}
          </p>
        )}

        {timedSegments && timedSegments.length > 0 && (
          <>
            <div className="flex items-center gap-3 mb-3 text-xs text-gray-500 font-semibold">
              <span>{timedSegments.length} segments</span>
              <span>·</span>
              <span>Total duration: {formatTime(totalDuration)}</span>
            </div>
            <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {timedSegments.map((seg, i) => (
                <div
                  key={i}
                  className="flex gap-3 items-start p-3 rounded-lg border border-gray-100 bg-gray-50 hover:bg-blue-50 hover:border-blue-200 transition"
                >
                  <span className="font-mono text-xs text-blue-600 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded shrink-0 mt-0.5">
                    {formatTime(seg.start)}–{formatTime(seg.end)}
                  </span>
                  <span className="text-sm text-gray-800">{seg.text}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {timedSegments && timedSegments.length === 0 && (
          <p className="text-sm text-gray-400 italic text-center py-4">
            No segments found in transcript_timed.json.
          </p>
        )}

        {!timedSegments && !error && !loading && (
          <p className="text-sm text-gray-400 italic text-center py-6">
            Click "Load Timed Segments" to see the timestamped breakdown of the transcript.
          </p>
        )}
      </div>
    </div>
  );
}