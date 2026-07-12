import React, { useCallback, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  CheckCircle2,
  Download,
  FileText,
  Languages,
  Loader2,
  UploadCloud,
  X
} from "lucide-react";
import "./styles.css";

type JobStatus = "queued" | "processing" | "complete" | "failed";

type JobState = {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
  download_url?: string;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws");

const LANGUAGES = [
  "Arabic",
  "English",
  "French",
  "German",
  "Japanese",
  "Korean",
  "Portuguese",
  "Spanish"
];

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [targetLanguage, setTargetLanguage] = useState("Arabic");
  const [job, setJob] = useState<JobState | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  const canSubmit = useMemo(() => Boolean(file) && !job, [file, job]);

  const pickFile = useCallback((incoming: File | null) => {
    setError("");
    setJob(null);
    if (!incoming) return;
    if (incoming.type !== "application/pdf") {
      setError("Upload a PDF file.");
      return;
    }
    setFile(incoming);
  }, []);

  const submit = async () => {
    if (!file) return;

    setError("");
    const body = new FormData();
    body.append("file", file);
    body.append("source_language", sourceLanguage);
    body.append("target_language", targetLanguage);

    try {
      const response = await fetch(`${API_URL}/api/jobs`, {
        method: "POST",
        body
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const created = (await response.json()) as JobState;
      setJob(created);

      const socket = new WebSocket(`${WS_URL}/ws/jobs/${created.job_id}`);
      socket.onmessage = (event) => {
        const next = JSON.parse(event.data) as JobState;
        setJob(next);
        if (next.status === "complete" || next.status === "failed") {
          socket.close();
        }
      };
      socket.onerror = () => {
        setError("Live progress disconnected. The job may still be running.");
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setJob(null);
    }
  };

  return (
    <main className="min-h-screen bg-mist text-ink">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 py-6 sm:px-8 lg:px-10">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-5">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-ink text-white">
              <Languages size={22} />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-normal">Noetica</h1>
              <p className="text-sm text-neutral-600">Layout-preserving PDF translation</p>
            </div>
          </div>
          {job?.status === "complete" && job.download_url ? (
            <a className="inline-flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white shadow-shad transition hover:bg-teal-800" href={`${API_URL}${job.download_url}`}>
              <Download size={17} />
              Download PDF
            </a>
          ) : null}
        </header>

        <div className="grid flex-1 gap-6 py-6 lg:grid-cols-[minmax(0,1.1fr)_360px]">
          <section
            className={`flex min-h-[460px] flex-col items-center justify-center rounded-lg border-2 border-dashed bg-white p-6 text-center shadow-shad transition ${
              dragging ? "border-brand ring-4 ring-teal-100" : "border-line"
            }`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              pickFile(event.dataTransfer.files.item(0));
            }}
          >
            <input
              ref={inputRef}
              className="hidden"
              type="file"
              accept="application/pdf"
              onChange={(event) => pickFile(event.target.files?.item(0) ?? null)}
            />

            <div className="grid h-20 w-20 place-items-center rounded-full bg-teal-50 text-brand">
              <UploadCloud size={38} />
            </div>
            <h2 className="mt-5 text-3xl font-semibold tracking-normal">Drop a PDF to translate</h2>
            <p className="mt-3 max-w-lg text-base leading-7 text-neutral-600">
              The backend extracts text positions, translates with Groq, redacts the original text, and redraws the translation in place.
            </p>

            {file ? (
              <div className="mt-6 flex w-full max-w-xl items-center justify-between gap-4 rounded-md border border-line bg-neutral-50 p-4 text-left">
                <div className="flex min-w-0 items-center gap-3">
                  <FileText className="shrink-0 text-brand" size={28} />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-neutral-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
                <button
                  className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-line text-neutral-600 transition hover:bg-white hover:text-ink"
                  title="Remove file"
                  onClick={() => {
                    setFile(null);
                    setJob(null);
                  }}
                >
                  <X size={17} />
                </button>
              </div>
            ) : null}

            <div className="mt-7 flex flex-wrap justify-center gap-3">
              <button
                className="inline-flex h-11 items-center gap-2 rounded-md border border-line bg-white px-5 text-sm font-medium shadow-sm transition hover:bg-neutral-50"
                onClick={() => inputRef.current?.click()}
              >
                <UploadCloud size={18} />
                Select PDF
              </button>
              <button
                className="inline-flex h-11 items-center gap-2 rounded-md bg-ink px-5 text-sm font-medium text-white shadow-shad transition enabled:hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-45"
                disabled={!canSubmit}
                onClick={submit}
              >
                {job ? <Loader2 className="animate-spin" size={18} /> : <ArrowRight size={18} />}
                Translate
              </button>
            </div>

            {error ? <p className="mt-4 text-sm text-ember">{error}</p> : null}
          </section>

          <aside className="flex flex-col gap-4">
            <div className="rounded-lg border border-line bg-white p-5 shadow-shad">
              <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-500">Languages</h2>
              <div className="mt-5 grid gap-4">
                <label className="grid gap-2 text-sm font-medium">
                  Source
                  <select className="h-11 rounded-md border border-line bg-white px-3 text-sm" value={sourceLanguage} onChange={(event) => setSourceLanguage(event.target.value)}>
                    <option value="auto">Auto detect</option>
                    {LANGUAGES.map((language) => (
                      <option key={language} value={language}>{language}</option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-2 text-sm font-medium">
                  Target
                  <select className="h-11 rounded-md border border-line bg-white px-3 text-sm" value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value)}>
                    {LANGUAGES.map((language) => (
                      <option key={language} value={language}>{language}</option>
                    ))}
                  </select>
                </label>
              </div>
            </div>

            <div className="rounded-lg border border-line bg-white p-5 shadow-shad">
              <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-500">Progress</h2>
              <div className="mt-5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium capitalize">{job?.status ?? "idle"}</span>
                  <span className="text-neutral-500">{job ? Math.round(job.progress) : 0}%</span>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-neutral-100">
                  <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${job?.progress ?? 0}%` }} />
                </div>
                <p className="mt-4 min-h-10 text-sm leading-6 text-neutral-600">
                  {job?.message ?? "Waiting for a PDF."}
                </p>
                {job?.status === "complete" ? (
                  <div className="mt-4 flex items-center gap-2 text-sm font-medium text-brand">
                    <CheckCircle2 size={18} />
                    Translation ready
                  </div>
                ) : null}
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
