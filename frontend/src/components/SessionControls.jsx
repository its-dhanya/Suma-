import React from "react";

export default function SessionControls({ onStart, onStop, loading, isRecording, sessionFolder }) {
  return (
    <div className="text-center mb-6">
      {!isRecording ? (
        <button
          onClick={onStart}
          disabled={loading}
          className="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          {loading ? "Recording…" : "Start Recording"}
        </button>
      ) : (
        <button
          onClick={onStop}
          className="px-6 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Stop Recording
        </button>
      )}
      {sessionFolder && (
        <p className="mt-2 text-sm text-gray-700">
          Session folder: <code>{sessionFolder}</code>
        </p>
      )}
    </div>
  );
}
