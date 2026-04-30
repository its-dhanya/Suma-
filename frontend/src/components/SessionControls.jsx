import React, { useEffect, useState } from "react";

export default function SessionControls({ onStart, onStop, loading, isRecording, sessionFolder }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("http://localhost:8000/session-status");
        if (res.ok) setStatus(await res.json());
      } catch { /* silently ignore */ }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, []);

  const captureMode = status?.capture_mode;

  return (
    <div className="text-center mb-6 space-y-3">
      <div className="flex justify-center gap-3 flex-wrap">
        {!isRecording ? (
          <button
            onClick={onStart}
            disabled={loading}
            className="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition duration-300"
          >
            {loading ? "Starting…" : "▶ Start Recording"}
          </button>
        ) : (
          <button
            onClick={onStop}
            className="px-6 py-2 bg-red-600 text-white rounded hover:bg-red-700 font-semibold transition duration-300"
          >
            ■ Stop Recording
          </button>
        )}
      </div>

      {/* Live recording pulse */}
      {isRecording && (
        <div className="flex justify-center items-center gap-2 text-sm text-red-600 font-semibold">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
          Recording in progress…
        </div>
      )}

      {/* Status pills */}
      {status && (
        <div className="flex justify-center gap-2 flex-wrap text-xs font-semibold mt-1">
          <span className={`px-3 py-1 rounded-full border ${
            status.audio_alive
              ? "bg-green-100 text-green-700 border-green-300"
              : "bg-gray-100 text-gray-500 border-gray-300"
          }`}>
            🎙 Audio {status.audio_alive ? "live" : "idle"}
          </span>
          <span className={`px-3 py-1 rounded-full border ${
            status.screen_alive
              ? "bg-green-100 text-green-700 border-green-300"
              : "bg-gray-100 text-gray-500 border-gray-300"
          }`}>
            📷 Capture {status.screen_alive ? "live" : "idle"}
          </span>
          {captureMode && (
            <span className={`px-3 py-1 rounded-full border ${
              captureMode === "esp32"
                ? "bg-indigo-100 text-indigo-700 border-indigo-300"
                : "bg-yellow-100 text-yellow-700 border-yellow-300"
            }`}>
              {captureMode === "esp32" ? "🔌 ESP32-CAM" : "🖥 Screen capture"}
            </span>
          )}
        </div>
      )}

      {sessionFolder && (
        <p className="mt-1 text-sm text-gray-600">
          Session: <code className="bg-gray-100 px-2 py-0.5 rounded text-indigo-700">{sessionFolder}</code>
        </p>
      )}
    </div>
  );
}