import React, { useState } from "react";
import { MessageSquare, Files, Users, LogOut, Plus, Edit2, Trash2, Check, X, ThumbsDown } from "lucide-react";
import { Conversation } from "../hooks/useChat";

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: number | null;
  setActiveConversationId: (id: number | null) => void;
  createConversation: () => void;
  deleteConversation: (id: number) => void;
  renameConversation: (id: number, titulo: string) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isAdmin: boolean;
  userEmail: string | null;
  onLogout: () => void;
}

export function Sidebar({
  conversations,
  activeConversationId,
  setActiveConversationId,
  createConversation,
  deleteConversation,
  renameConversation,
  activeTab,
  setActiveTab,
  isAdmin,
  userEmail,
  onLogout,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const handleStartRename = (c: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(c.id);
    setEditTitle(c.titulo);
  };

  const handleSaveRename = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      renameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <div className="flex h-screen w-80 flex-col border-r border-border bg-sidebar">
      {/* User profile & Navigation */}
      <div className="flex flex-col p-4 border-b border-border">
        <div className="flex items-center space-x-3 mb-6">
          <img
            src="https://www.uco.es/investigacion/proyectos/SEBASENet/images/thumb/Logo_US.png/655px-Logo_US.png"
            alt="US Logo"
            className="h-10 w-auto filter brightness-110"
          />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              Conectado como
            </p>
            <p className="truncate text-sm font-medium text-white" title={userEmail || ""}>
              {userEmail || "Usuario"}
            </p>
          </div>
        </div>

        {/* Tab buttons */}
        <div className="space-y-1">
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex w-full items-center space-x-3 rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
              activeTab === "chat"
                ? "bg-accent text-white"
                : "text-gray-400 hover:bg-[#1f222d] hover:text-white"
            }`}
          >
            <MessageSquare size={18} />
            <span>Chat con Asistente</span>
          </button>

          <button
            onClick={() => setActiveTab("documents")}
            className={`flex w-full items-center space-x-3 rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
              activeTab === "documents"
                ? "bg-accent text-white"
                : "text-gray-400 hover:bg-[#1f222d] hover:text-white"
            }`}
          >
            <Files size={18} />
            <span>Documentos</span>
          </button>

          {isAdmin && (
            <>
              <button
                onClick={() => setActiveTab("users")}
                className={`flex w-full items-center space-x-3 rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
                  activeTab === "users"
                    ? "bg-accent text-white"
                    : "text-gray-400 hover:bg-[#1f222d] hover:text-white"
                }`}
              >
                <Users size={18} />
                <span>Administrar Usuarios</span>
              </button>

              <button
                onClick={() => setActiveTab("feedback")}
                className={`flex w-full items-center space-x-3 rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
                  activeTab === "feedback"
                    ? "bg-accent text-white"
                    : "text-gray-400 hover:bg-[#1f222d] hover:text-white"
                }`}
              >
                <ThumbsDown size={18} />
                <span>Feedback Negativo</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Conversations history (Only shown when on Chat tab) */}
      <div className="flex-1 overflow-y-auto px-2 py-4">
        {activeTab === "chat" ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between px-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
                Chats Recientes
              </span>
              <button
                onClick={createConversation}
                className="flex items-center space-x-1 rounded bg-[#0d0e12] border border-border p-1.5 text-xs text-accent hover:text-white hover:bg-accent transition-all"
                title="Nuevo chat"
              >
                <Plus size={14} />
              </button>
            </div>

            <div className="space-y-1">
              {conversations.map((c) => {
                const isActive = activeConversationId === c.id;
                const isEditing = editingId === c.id;

                return (
                  <div
                    key={c.id}
                    onClick={() => !isEditing && setActiveConversationId(c.id)}
                    className={`group relative flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium cursor-pointer transition-all ${
                      isActive
                        ? "bg-[#1f222d] text-white border-l-4 border-accent"
                        : "text-gray-400 hover:bg-[#14161f] hover:text-white"
                    }`}
                  >
                    {isEditing ? (
                      <div className="flex w-full items-center space-x-1" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="w-full rounded border border-border bg-[#0d0e12] px-2 py-1 text-xs text-white focus:outline-none focus:border-accent"
                          autoFocus
                        />
                        <button
                          onClick={(e) => handleSaveRename(c.id, e)}
                          className="text-green-500 hover:text-green-400 p-1"
                        >
                          <Check size={14} />
                        </button>
                        <button
                          onClick={handleCancelRename}
                          className="text-red-500 hover:text-red-400 p-1"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ) : (
                      <>
                        <span className="truncate pr-8">{c.titulo}</span>
                        {isActive && (
                          <div className="absolute right-2 hidden space-x-1 group-hover:flex bg-[#1f222d] pl-2">
                            <button
                              onClick={(e) => handleStartRename(c, e)}
                              className="text-gray-400 hover:text-white p-1"
                              title="Renombrar chat"
                            >
                              <Edit2 size={12} />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                if (confirm("¿Estás seguro de que deseas eliminar esta conversación?")) {
                                  deleteConversation(c.id);
                                }
                              }}
                              className="text-accent hover:text-red-400 p-1"
                              title="Eliminar chat"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-center px-4">
            <p className="text-xs text-gray-500">
              Navega entre pestañas para ver las herramientas de administración y listado de conocimiento.
            </p>
          </div>
        )}
      </div>

      {/* Logout button */}
      <div className="p-4 border-t border-border bg-[#0b0c10]">
        <button
          onClick={onLogout}
          className="flex w-full items-center justify-center space-x-2 rounded-lg border border-border bg-[#0d0e12] px-4 py-2.5 text-sm font-medium text-gray-400 transition-all hover:bg-accent hover:text-white"
        >
          <LogOut size={16} />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </div>
  );
}
