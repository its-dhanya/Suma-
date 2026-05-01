import React, { useEffect, useState } from "react";

export default function SessionControls({ onStart, onStop, loading, isRecording, sessionFolder }) {
  const [status,          setStatus]          = useState(null);
  const [selectedMode,    setSelectedMode]    = useState("esp32");
  const [wasRecording,    setWasRecording]    = useState(false);
  const [autoTranscribing, setAutoTranscribing] = useState(false);

  // Track when recording stops to show auto-transcribing banner
  useEffect(() => {
    if (wasRecording && !isRecording) {
      setAutoTranscribing(true);
      // Audio length varies; hide banner after 5 minutes max
      const t = setTimeout(() => setAutoTranscribing(false), 5 * 60 * 1000);
      return () => clearTimeout(t);
    }
    setWasRecording(isRecording);
  }, [isRecording]);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("http://localhost:8000/session-status");
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
          // When audio thread dies, transcription is likely done
          if (!data.audio_alive) setAutoTranscribing(false);
        }
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
          <div className="flex flex-col items-center gap-3">
            <div className="flex bg-gray-100 p-1 rounded-lg">
              <button
                className={`px-4 py-1.5 rounded-md text-sm font-semibold transition-colors ${
                  selectedMode === "esp32"
                    ? "bg-white text-indigo-700 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setSelectedMode("esp32")}
              >
                ESP32-CAM
              </button>
              <button
                className={`px-4 py-1.5 rounded-md text-sm font-semibold transition-colors ${
                  selectedMode === "screen"
                    ? "bg-white text-indigo-700 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setSelectedMode("screen")}
              >
                Screen Capture
              </button>
            </div>
            <button
              onClick={() => onStart(selectedMode)}
            disabled={loading}
            className="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition duration-300"
          >
              {loading ? "Starting…" : "▶ Start Recording"}
            </button>
          </div>
        ) : (
          <button
            onClick={onStop}
            className="px-6 py-2 bg-red-600 text-white rounded hover:bg-red-700 font-semibold transition duration-300"
          >
            ■ Stop Recording
          </button>
        )}
      </div>

      {/* Auto-transcribing indicator */}
      {!isRecording && autoTranscribing && (
        <div className="flex justify-center items-center gap-2 text-sm text-blue-600 font-semibold mt-2">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
          Auto-transcribing audio in background…
        </div>
      )}

      {/* Camera syncing indicator after stop */}
      {!isRecording && status?.guna_syncing && (
        <div className="flex justify-center items-center gap-2 text-sm text-yellow-600 font-semibold mt-2">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-500 animate-pulse" />
          Camera syncing delayed photos…
        </div>
      )}

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
            status.screen_alive || status.guna_syncing
              ? "bg-green-100 text-green-700 border-green-300"
              : "bg-gray-100 text-gray-500 border-gray-300"
          }`}>
            📷 Capture {(status.screen_alive || status.guna_syncing) ? (status.guna_syncing && !status.screen_alive ? "syncing" : "live") : "idle"}
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