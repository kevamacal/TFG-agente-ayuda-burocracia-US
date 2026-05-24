import React, { useState, useEffect } from "react";
import { MessageSquare, Calendar, BookOpen, Frown, RefreshCw } from "lucide-react";
import Cookies from "js-cookie";
import { API_URL } from "@/utils/api";
import ReactMarkdown from "react-markdown";

interface FeedbackItem {
  mensaje_id: number;
  conversacion_id: number;
  pregunta_usuario: string;
  respuesta_asistente: string;
  referencias: string; // JSON string
  feedback_comentario: string;
  fecha_creacion: string;
}

export function FeedbackList() {
  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const token = Cookies.get("auth_token");

  const fetchFeedback = async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/admin/feedback/negativo`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setFeedbackItems(data);
      } else {
        setError("Error al obtener los registros de feedback negativo.");
      }
    } catch (err) {
      setError("Error de conexión al servidor.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeedback();
  }, []);

  return (
    <div className="flex flex-1 flex-col bg-background text-textMain p-8 overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-8 animate-fade-in">
        
        {/* Title */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-textMain flex items-center space-x-2">
              <Frown size={24} className="text-accent" />
              <span>👎 Feedback Negativo y Reportes</span>
            </h2>
            <p className="mt-1 text-sm text-textMuted">
              Listado de respuestas valoradas negativamente por los usuarios para auditoría y mejora del RAG.
            </p>
          </div>
          <button
            onClick={fetchFeedback}
            disabled={loading}
            className="flex items-center space-x-2 rounded-lg border border-border bg-sidebar px-4 py-2 text-sm font-semibold text-textMuted hover:text-textMain transition-all disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span>Refrescar</span>
          </button>
        </div>

        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {feedbackItems.length === 0 && !loading && !error ? (
          <div className="rounded-xl border border-border bg-sidebar p-8 text-center text-textMuted">
            No hay reportes de feedback negativo registrados. ¡El asistente está respondiendo bien!
          </div>
        ) : (
          <div className="space-y-4">
            {feedbackItems.map((item) => {
              let parsedRefs: string[] = [];
              if (item.referencias) {
                try {
                  parsedRefs = JSON.parse(item.referencias);
                } catch {
                  parsedRefs = [];
                }
              }

              const dateStr = item.fecha_creacion
                ? new Date(item.fecha_creacion).toLocaleDateString("es-ES", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "";

              return (
                <div
                  key={item.mensaje_id}
                  className="rounded-xl border border-border bg-sidebar p-6 shadow-md space-y-4 hover:border-accent/15 transition-all"
                >
                  {/* Top info row */}
                  <div className="flex flex-wrap items-center justify-between text-xs text-textMuted border-b border-border/40 pb-3 gap-2">
                    <div className="flex items-center space-x-4">
                      <span className="flex items-center space-x-1">
                        <Calendar size={12} />
                        <span>{dateStr}</span>
                      </span>
                      <span>•</span>
                      <span>Conversación ID: #{item.conversacion_id}</span>
                    </div>
                  </div>

                  {/* Q & A Section */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-lg bg-inputBg border border-border/70 p-4 space-y-1.5">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-textMuted flex items-center space-x-1.5">
                        <MessageSquare size={12} className="text-accent" />
                        <span>Pregunta del Usuario</span>
                      </h4>
                      <p className="text-sm text-textMain whitespace-pre-wrap">{item.pregunta_usuario}</p>
                    </div>

                    <div className="rounded-lg bg-inputBg border border-border/70 p-4 space-y-1.5">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-red-400 flex items-center space-x-1.5">
                        <Frown size={12} />
                        <span>Respuesta Evaluada</span>
                      </h4>
                      <div className="text-sm text-textMain leading-relaxed">
                        <ReactMarkdown
                          components={{
                            p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                            ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-2 pl-1 space-y-0.5" {...props} />,
                            ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-2 pl-1 space-y-0.5" {...props} />,
                            li: ({ node, ...props }) => <li className="mb-0.5" {...props} />,
                            strong: ({ node, ...props }) => <strong className="font-bold text-textMain" {...props} />,
                            a: ({ node, ...props }) => <a className="text-accent hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
                            code: ({ node, ...props }) => <code className="bg-background border border-border/50 px-1 py-0.5 rounded text-xs font-mono text-accent" {...props} />,
                          }}
                        >
                          {item.respuesta_asistente}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>

                  {/* Feedback comment */}
                  {item.feedback_comentario && (
                    <div className="rounded-lg bg-red-500/5 border border-red-500/10 p-4 space-y-1">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-red-400">
                        Motivo del reporte / Comentario del usuario:
                      </h4>
                      <p className="text-xs text-textMain italic">
                        "{item.feedback_comentario}"
                      </p>
                    </div>
                  )}

                  {/* References used */}
                  {parsedRefs.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-textMuted flex items-center space-x-1.5">
                        <BookOpen size={12} />
                        <span>Documentos de RAG Consultados</span>
                      </h4>
                      <ul className="grid gap-1.5 sm:grid-cols-2 text-xs text-textMuted">
                        {parsedRefs.map((ref, idx) => (
                          <li key={idx} className="flex items-center space-x-2 rounded bg-background px-3 py-2 border border-border/50">
                            <span className="h-1.5 w-1.5 rounded-full bg-accent shrink-0" />
                            <span className="truncate">{ref}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
}
