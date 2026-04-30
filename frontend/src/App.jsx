import React, { useState, useEffect } from "react";
import SessionControls from "./components/SessionControls";
import TranscriptView from "./components/TranscriptView";
import SummaryCard from "./components/SummaryCard";
import { jsPDF } from "jspdf";
import myBackground from "/image.png";

const SYSTEM_PROMPT = "Provide a concise and comprehensive summary of the lecture content.";

// ── Spinner ────────────────────────────────────────────────────────────────────
function Spinner() {
  return (
    <div
      className="spinner inline-block"
      style={{
        border: "4px solid #f3f3f3",
        borderTop: "4px solid #3498db",
        borderRadius: "50%",
        width: "18px",
        height: "18px",
        animation: "spin 2s linear infinite",
      }}
    >
      <style>{`@keyframes spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }`}</style>
    </div>
  );
}

// ── YouTube link + OCR controls (Video tab) ───────────────────────────────────
function VideoUploadControls({ setTranscript }) {
  const [youtubeURL, setYoutubeURL]   = useState("");
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [ocrResults, setOcrResults]   = useState(null);
  const [loadingOcr, setLoadingOcr]   = useState(false);
  const [ocrError, setOcrError]       = useState("");

  const handleUpload = async () => {
    if (!youtubeURL) return;
    setLoadingUpload(true);
    try {
      const res = await fetch(
        `http://localhost:8000/youtube-transcript?videoURL=${encodeURIComponent(youtubeURL)}`
      );
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setTranscript(data.transcript);
    } catch (error) {
      console.error("Error uploading YouTube video:", error);
    } finally {
      setLoadingUpload(false);
    }
  };

  const handleOcr = async () => {
    setLoadingOcr(true);
    setOcrError("");
    setOcrResults(null);
    try {
      const res = await fetch("http://localhost:8000/ocr", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "OCR failed");
      setOcrResults(data.ocr_results);
    } catch (e) {
      setOcrError(e.message);
    } finally {
      setLoadingOcr(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* YouTube */}
      <div className="my-6 p-4 border rounded shadow-sm transition transform hover:scale-105 hover:shadow-xl">
        <h3 className="text-xl font-semibold mb-2">Insert a YouTube Video Link</h3>
        <input
          type="text"
          value={youtubeURL}
          onChange={(e) => setYoutubeURL(e.target.value)}
          placeholder="Enter YouTube video URL"
          className="border rounded p-2 w-full mb-4 focus:outline-none focus:ring-2 focus:ring-blue-600"
        />
        <button
          onClick={handleUpload}
          disabled={loadingUpload}
          className={`flex items-center gap-2 px-4 py-2 rounded font-semibold transition duration-300 ${
            loadingUpload
              ? "bg-blue-200 text-gray-500 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {loadingUpload && <Spinner />}
          {loadingUpload ? "Uploading..." : "Submit YouTube Link"}
        </button>
      </div>

      {/* Board OCR */}
      <div className="p-4 border rounded shadow-sm transition transform hover:scale-105 hover:shadow-xl">
        <h3 className="text-xl font-semibold mb-2">Board OCR</h3>
        <p className="text-sm text-gray-600 mb-3">
          Run Tesseract OCR (with OpenCV perspective correction) on all captured board images
          from the current session.
        </p>
        <button
          onClick={handleOcr}
          disabled={loadingOcr}
          className={`flex items-center gap-2 px-4 py-2 rounded font-semibold transition duration-300 ${
            loadingOcr
              ? "bg-indigo-200 text-gray-500 cursor-not-allowed"
              : "bg-indigo-600 text-white hover:bg-indigo-700"
          }`}
        >
          {loadingOcr && <Spinner />}
          {loadingOcr ? "Running OCR…" : "Run OCR on Session Images"}
        </button>

        {ocrError && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            {ocrError}
          </p>
        )}

        {ocrResults && (
          <div className="mt-4 space-y-3 max-h-80 overflow-y-auto">
            {ocrResults.map((item, i) => {
              const [fname, text] = Object.entries(item)[0];
              return (
                <div key={i} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <p className="font-mono text-xs text-indigo-700 mb-1">{fname}</p>
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                    {text || "(no text extracted)"}
                  </pre>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
function App() {
  const [sessionFolder, setSessionFolder] = useState("");
  const [transcript, setTranscript]       = useState("");
  const [summary, setSummary]             = useState(null);
  const [jobId, setJobId]                 = useState(null);
  const [activeTab, setActiveTab]         = useState("home");
  const [loading, setLoading]             = useState({
    session: false,
    transcribe: false,
    summarize: false,
  });
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    console.log("Updated summary:", summary);
  }, [summary]);

  const startSession = async () => {
    setLoading((prev) => ({ ...prev, session: true }));
    setIsRecording(true);
    try {
      const res  = await fetch("http://localhost:8000/start-session", { method: "POST" });
      const data = await res.json();
      setSessionFolder(data.session_folder);
    } catch (error) {
      console.error("Error starting session:", error);
    } finally {
      setLoading((prev) => ({ ...prev, session: false }));
    }
  };

  const stopSession = async () => {
    try {
      await fetch("http://localhost:8000/stop-session", { method: "POST" });
      setIsRecording(false);
    } catch (error) {
      console.error("Error stopping session:", error);
    }
  };

  const doTranscribe = async () => {
    setLoading((prev) => ({ ...prev, transcribe: true }));
    try {
      const res  = await fetch("http://localhost:8000/transcribe", { method: "POST" });
      const data = await res.json();
      setTranscript(data.transcript);
    } catch (error) {
      console.error("Error transcribing:", error);
    } finally {
      setLoading((prev) => ({ ...prev, transcribe: false }));
    }
  };

  const startSummarization = async () => {
    setLoading((prev) => ({ ...prev, summarize: true }));
    try {
      const res = await fetch("http://localhost:8000/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ system_prompt: SYSTEM_PROMPT }),
      });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setJobId(data.jobId);
    } catch (error) {
      console.error("Error starting summarization:", error);
      setLoading((prev) => ({ ...prev, summarize: false }));
    }
  };

  // Poll summarization job
  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      try {
        const res  = await fetch(`http://localhost:8000/summary/${jobId}`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();
        if (data.status === "done" || data.status === "error") {
          if (data.status === "done") setSummary(data.result);
          else console.error("Summarization job failed:", data.result);
          setJobId(null);
          setLoading((prev) => ({ ...prev, summarize: false }));
          clearInterval(interval);
        }
      } catch (error) {
        console.error("Error polling summary job:", error);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [jobId]);

  // ── PDF export ───────────────────────────────────────────────────────────
  const exportPDF = () => {
    if (!summary) return;

    const doc        = new jsPDF({ unit: "pt", format: "letter" });
    const pageWidth  = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin     = 50;
    let y            = margin;
    const lineSpacing    = 16;
    const sectionSpacing = 30;

    const ensurePage = (needed = 60) => {
      if (y + needed > pageHeight - margin) { doc.addPage(); y = margin; }
    };

    const formatContent = (val) => {
      if (!val) return "";
      if (typeof val === "string") return val;
      if (Array.isArray(val)) {
        return val.map((item) => {
          if (typeof item === "string") return `• ${item}`;
          if (item.question && item.answer) return `Q: ${item.question}\nA: ${item.answer}`;
          if (item.title && item.url) return `${item.title} (${item.type})\n${item.url}`;
          return JSON.stringify(item, null, 2);
        }).join("\n\n");
      }
      if (typeof val === "object") return JSON.stringify(val, null, 2);
      return String(val);
    };

    const sections = [
      { title: "Overview",             color: [90,  120, 255], content: formatContent(summary.overview) },
      { title: "Core Concepts",        color: [120,  90, 255], content: formatContent(summary.core_concepts) },
      { title: "Detailed Explanation", color: [70,  150, 200], content: formatContent(summary.detailed_explanation) },
      { title: "Examples",             color: [70,  180, 120], content: formatContent(summary.examples) },
      { title: "Key Takeaways",        color: [220, 140,  60], content: formatContent(summary.takeaways) },
      { title: "Revision Questions",   color: [200,  80,  80], content: formatContent(summary.questions) },
      { title: "Resources",            color: [140, 120,  90], content: formatContent(summary.resources) },
    ];

    // Header
    doc.setFillColor(40, 60, 120);
    doc.rect(0, 0, pageWidth, 120, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(36);
    doc.setTextColor(255, 255, 255);
    doc.text("SUM AI NOTES", pageWidth / 2, 70, { align: "center" });
    doc.setFontSize(16);
    doc.setFont("helvetica", "italic");
    doc.text("Smart Lecture Summary", pageWidth / 2, 95, { align: "center" });
    y = 150;

    sections.forEach((sec) => {
      if (!sec.content) return;
      ensurePage(100);
      doc.setFillColor(...sec.color);
      doc.rect(margin - 8, y - 18, pageWidth - margin * 2 + 16, 26, "F");
      doc.setFont("helvetica", "bold");
      doc.setFontSize(18);
      doc.setTextColor(255, 255, 255);
      doc.text(sec.title, margin, y);
      y += sectionSpacing;
      doc.setFont("times", "normal");
      doc.setFontSize(12);
      doc.setTextColor(30, 30, 30);
      const lines = doc.splitTextToSize(sec.content, pageWidth - margin * 2);
      lines.forEach((line) => { ensurePage(); doc.text(line, margin, y); y += lineSpacing; });
      y += 20;
    });

    // Footer
    const pages = doc.internal.getNumberOfPages();
    doc.setFont("helvetica", "italic");
    doc.setFontSize(10);
    doc.setTextColor(120);
    for (let i = 1; i <= pages; i++) {
      doc.setPage(i);
      doc.text(`Page ${i} of ${pages}`, pageWidth - margin, pageHeight - 20, { align: "right" });
    }

    doc.save("Sum_AI_Lecture_Notes.pdf");
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen text-gray-900 flex flex-col items-center justify-start p-10 relative overflow-hidden">
      {/* Background */}
      <div
        className="absolute top-0 left-0 w-full h-full"
        style={{
          backgroundImage: `url(${myBackground})`,
          backgroundRepeat: "repeat",
          backgroundSize: "300px 300px",
          zIndex: -1,
          opacity: 0.4,
          animation: "movebg 40s linear infinite",
        }}
      />

      {/* Nav */}
      <nav className="w-full max-w-5xl mb-6">
        <ul className="flex justify-around bg-white/90 backdrop-blur-md rounded-full p-3 shadow-md">
          {[
            { id: "home",       label: "Home",       active: "bg-blue-600" },
            { id: "video",      label: "Video",      active: "bg-indigo-600" },
            { id: "transcript", label: "Transcript", active: "bg-green-600" },
            { id: "summary",    label: "Summary",    active: "bg-purple-600" },
          ].map(({ id, label, active }) => (
            <li key={id}>
              <button
                onClick={() => setActiveTab(id)}
                className={`px-4 py-2 font-semibold rounded-full transition duration-300 ${
                  activeTab === id ? `${active} text-white` : "text-gray-800 hover:bg-gray-100"
                }`}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="w-full max-w-5xl bg-white/90 backdrop-blur-lg rounded-3xl shadow-2xl border border-gray-300 p-10 space-y-8">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-800 to-indigo-800 rounded-3xl p-16 text-center shadow-2xl transition-transform">
          <h1 className="text-9xl font-extrabold text-white drop-shadow-xl animate-pulse">SumAI</h1>
          <p className="mt-6 text-4xl text-gray-200 italic tracking-wide">
            Your Smart Note-Taking Assistant
          </p>
        </div>

        {/* ── HOME ── */}
        {activeTab === "home" && (
          <div className="text-center space-y-6">
            <h2 className="text-5xl font-bold">Welcome to SumAI</h2>
            <p className="text-xl text-gray-700 max-w-3xl mx-auto">
              SumAI is designed to transform the way you capture and review important information
              from lectures and meetings. Leveraging advanced AI, SumAI makes note-taking effortless.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-8">
              {[
                { title: "Record & Upload",  body: "Record your lectures or upload a YouTube video to instantly convert audio to text." },
                { title: "Transcription",    body: "View detailed transcripts of your recordings with high accuracy." },
                { title: "Summarization",    body: "Generate concise summaries with actionable insights and resource recommendations." },
              ].map(({ title, body }) => (
                <div key={title} className="group p-6 border rounded-xl shadow-lg transition transform hover:scale-105 hover:shadow-2xl hover:bg-gradient-to-r hover:from-blue-800 hover:to-indigo-800">
                  <h3 className="text-2xl font-bold mb-2 group-hover:text-white">{title}</h3>
                  <p className="text-gray-600 group-hover:text-white">{body}</p>
                </div>
              ))}
            </div>
            <p className="text-lg text-gray-600 mt-8">
              Navigate through the tabs above to start recording, view transcripts, and generate summaries.
            </p>
          </div>
        )}

        {/* ── VIDEO ── */}
        {activeTab === "video" && (
          <div className="space-y-6">
            <SessionControls
              onStart={startSession}
              onStop={stopSession}
              loading={loading.session}
              isRecording={isRecording}
              sessionFolder={sessionFolder}
            />
            <VideoUploadControls setTranscript={setTranscript} />
          </div>
        )}

        {/* ── TRANSCRIPT ── */}
        {activeTab === "transcript" && (
          <div className="space-y-6">
            <div className="flex justify-center">
              <button
                onClick={doTranscribe}
                disabled={loading.transcribe}
                className={`mt-6 px-6 py-3 rounded-lg font-semibold shadow-lg transition duration-300 ease-in-out ${
                  loading.transcribe
                    ? "bg-blue-200 text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
              >
                {loading.transcribe ? (
                  <span className="flex items-center gap-2"><Spinner /> Transcribing…</span>
                ) : (
                  "Transcribe Audio"
                )}
              </button>
            </div>
            <TranscriptView transcript={transcript} />
          </div>
        )}

        {/* ── SUMMARY ── */}
        {activeTab === "summary" && (
          <div className="space-y-6">
            <div className="flex justify-center gap-6">
              <button
                onClick={startSummarization}
                disabled={loading.summarize}
                className={`mt-4 px-6 py-3 rounded-lg font-semibold shadow-lg transition duration-300 ease-in-out ${
                  loading.summarize
                    ? "bg-green-200 text-gray-500 cursor-not-allowed"
                    : "bg-green-600 text-white hover:bg-green-700"
                }`}
              >
                {loading.summarize ? (
                  <span className="flex items-center gap-2"><Spinner /> Summarizing…</span>
                ) : (
                  "Generate Summary"
                )}
              </button>
              {summary && (
                <button
                  onClick={exportPDF}
                  className="mt-4 px-6 py-3 rounded-lg font-semibold shadow-lg bg-purple-700 text-white hover:bg-purple-800 transition duration-300"
                >
                  Export as PDF
                </button>
              )}
            </div>
            {summary && <SummaryCard summary={summary} />}
          </div>
        )}
      </div>

      <style>{`
        @keyframes movebg {
          0%   { background-position: 0% 100%; }
          100% { background-position: 0% 0%; }
        }
      `}</style>
    </div>
  );
}

export default App;