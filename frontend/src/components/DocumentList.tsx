import React, { useState, useEffect } from "react";
import { FileText, Trash2, Upload, AlertCircle, RefreshCw } from "lucide-react";
import Cookies from "js-cookie";
import { ConfirmModal } from "./ConfirmModal";

interface DocumentItem {
  nombre: string;
}

interface DocumentListProps {
  isAdmin: boolean;
}
import { API_URL } from "@/utils/api";

export function DocumentList({ isAdmin }: DocumentListProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<string | null>(null);

  const token = Cookies.get("auth_token");

  const fetchDocuments = async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/documentos`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      } else {
        setError("Error al obtener los documentos de la base vectorial.");
      }
    } catch (err) {
      setError("Error de conexión con el servidor.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const confirmDeleteDoc = (nombre: string) => {
    setDocToDelete(nombre);
    setIsDeleteModalOpen(true);
  };

  const handleDelete = async (nombre: string) => {
    if (!token) return;

    try {
      const encodedName = encodeURIComponent(nombre);
      const res = await fetch(`${API_URL}/admin/documentos?nombre=${encodedName}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        setDocuments((prev) => prev.filter((doc) => doc.nombre !== nombre));
        alert("Documento y vectores eliminados correctamente.");
      } else {
        alert("Error al eliminar el documento.");
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al intentar eliminar el documento.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type !== "application/pdf") {
        setUploadError("Solo se admiten archivos en formato PDF.");
        setSelectedFile(null);
      } else {
        setUploadError("");
        setSelectedFile(file);
      }
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !token) return;

    setUploading(true);
    setUploadError("");
    setUploadMessage("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch(`${API_URL}/admin/ingestar`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await res.json();
      if (res.status === 202) {
        setUploadMessage(`El archivo '${selectedFile.name}' se está indexando en segundo plano en Pinecone. Esto puede demorar unos minutos.`);
        setSelectedFile(null);
        // Refresh list in a few seconds
        setTimeout(fetchDocuments, 3000);
      } else {
        setUploadError(data.detail || "Error al subir el archivo.");
      }
    } catch (err) {
      setUploadError("Error de conexión al subir el documento.");
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  return (
    <div className="flex flex-1 flex-col bg-[#0d0e12] p-8 overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-8 animate-fade-in">
        
        {/* Title */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center space-x-2">
              <FileText size={24} className="text-accent" />
              <span>📚 Base de Conocimiento (Pinecone)</span>
            </h2>
            <p className="mt-1 text-sm text-gray-400">
              Inventario de normativas y PDFs que el asistente utiliza para dar respuestas en el RAG.
            </p>
          </div>
          <button
            onClick={fetchDocuments}
            disabled={loading}
            className="flex items-center space-x-2 rounded-lg border border-border bg-sidebar px-4 py-2 text-sm font-semibold text-gray-300 hover:text-white transition-all disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span>Refrescar</span>
          </button>
        </div>

        {/* Admin Upload Section */}
        {isAdmin && (
          <div className="rounded-xl border border-border bg-sidebar p-6 shadow-lg">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-4">
              ➕ Añadir nuevo documento PDF
            </h3>
            
            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div className="flex items-center justify-center rounded-lg border-2 border-dashed border-border/80 bg-[#0d0e12] px-6 py-6 transition-all hover:border-accent/40">
                <div className="text-center">
                  <Upload size={32} className="mx-auto text-gray-600 mb-2" />
                  <div className="flex text-sm text-gray-400">
                    <label className="relative cursor-pointer rounded-md font-semibold text-accent hover:text-accent-hover focus-within:outline-none">
                      <span>Seleccionar archivo PDF</span>
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={handleFileChange}
                        className="sr-only"
                      />
                    </label>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Solo documentos PDF hasta 10MB</p>
                </div>
              </div>

              {selectedFile && (
                <div className="flex items-center justify-between rounded-lg bg-accent/5 border border-accent/10 px-4 py-2 text-xs">
                  <span className="font-semibold text-white truncate max-w-[80%]">
                    📄 {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="text-red-400 hover:text-red-300"
                  >
                    Quitar
                  </button>
                </div>
              )}

              {uploadError && (
                <div className="flex items-center space-x-2 rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-400">
                  <AlertCircle size={14} />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadMessage && (
                <div className="flex items-center space-x-2 rounded-lg bg-green-500/10 border border-green-500/20 p-3 text-xs text-green-400">
                  <span>{uploadMessage}</span>
                </div>
              )}

              {selectedFile && (
                <button
                  type="submit"
                  disabled={uploading}
                  className="w-full rounded-lg bg-accent py-2.5 text-sm font-semibold text-white shadow hover:bg-accent-hover disabled:opacity-50 transition-all"
                >
                  {uploading ? "Subiendo e indexando..." : "Subir y procesar documento"}
                </button>
              )}
            </form>
          </div>
        )}

        {/* Documents Listing */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 px-1">
            Archivos Indexados en Pinecone
          </h3>

          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-400">
              {error}
            </div>
          )}

          {documents.length === 0 && !loading && !error ? (
            <div className="rounded-xl border border-border bg-sidebar p-8 text-center text-gray-500">
              No hay documentos registrados actualmente en tu base de datos vectorial.
            </div>
          ) : (
            <div className="grid gap-3">
              {documents.map((doc, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between rounded-xl border border-border bg-sidebar px-5 py-4 shadow-sm hover:border-accent/20 transition-all"
                >
                  <div className="flex items-center space-x-4 min-w-0">
                    <div className="rounded-lg bg-[#0d0e12] border border-border p-2.5 text-gray-400">
                      <FileText size={20} />
                    </div>
                    <div className="min-w-0">
                      <h4 className="truncate text-sm font-semibold text-white" title={doc.nombre}>
                        {doc.nombre}
                      </h4>
                      <p className="text-xs text-gray-400 mt-0.5">
                        Disponible para búsqueda vectorial • Indexado
                      </p>
                    </div>
                  </div>

                  {isAdmin && (
                    <button
                      onClick={() => confirmDeleteDoc(doc.nombre)}
                      className="rounded-lg border border-border/80 bg-[#0d0e12] p-2.5 text-accent hover:bg-accent hover:text-white transition-all shadow-sm"
                      title="Eliminar del vector store"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

      </div>

      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setDocToDelete(null);
        }}
        onConfirm={() => {
          if (docToDelete) {
            handleDelete(docToDelete);
          }
        }}
        title="Eliminar documento e indexación"
        message={`¿Estás seguro de que deseas eliminar permanentemente el documento '${docToDelete}' y todos sus vectores indexados en Pinecone? Esta acción no se puede deshacer.`}
        confirmText="Eliminar"
        isDestructive={true}
      />
    </div>
  );
}
