import React, { useState, useEffect } from "react";
import { Users, UserPlus, Shield, Trash2, AlertCircle, CheckCircle } from "lucide-react";
import Cookies from "js-cookie";
import { ConfirmModal } from "./ConfirmModal";

interface UserItem {
  id: number;
  email: string;
  is_admin: boolean;
  fecha_creacion: string;
}

interface UserManagementProps {
  currentUserEmail: string | null;
}
import { API_URL } from "@/utils/api";

export function UserManagement({ currentUserEmail }: UserManagementProps) {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<{ id: number; email: string } | null>(null);

  // Create User form state
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [formSuccess, setFormSuccess] = useState("");
  const [formError, setFormError] = useState("");
  const [formLoading, setFormLoading] = useState(false);

  const token = Cookies.get("auth_token");

  const fetchUsers = async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/admin/usuarios`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      } else {
        setError("Error al obtener el listado de usuarios.");
      }
    } catch (err) {
      setError("Error de conexión al servidor.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAdmin = async (id: number, email: string, currentStatus: boolean) => {
    if (!token) return;
    if (email === currentUserEmail) return; // Prevent self-editing

    try {
      const res = await fetch(`${API_URL}/admin/usuarios/${id}/admin`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_admin: !currentStatus }),
      });

      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => (u.id === id ? { ...u, is_admin: !currentStatus } : u))
        );
      } else {
        alert("Error al actualizar los permisos del usuario.");
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al intentar cambiar el rol.");
    }
  };

  const confirmDeleteUser = (id: number, email: string) => {
    if (email === currentUserEmail) return; // Prevent self-deletion
    setUserToDelete({ id, email });
    setIsDeleteModalOpen(true);
  };

  const handleDeleteUser = async (id: number) => {
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/admin/usuarios/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        setUsers((prev) => prev.filter((u) => u.id !== id));
      } else {
        alert("Error al eliminar el usuario.");
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al intentar borrar la cuenta.");
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    setFormSuccess("");
    setFormLoading(true);

    if (!newEmail || !newPassword) {
      setFormError("Por favor, rellene todos los campos obrigatorios.");
      setFormLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/admin/usuarios`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          email: newEmail,
          password: newPassword,
          is_admin: newIsAdmin,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setFormSuccess(`Usuario '${newEmail}' creado correctamente.`);
        setNewEmail("");
        setNewPassword("");
        setNewIsAdmin(false);
        fetchUsers();
      } else {
        setFormError(data.detail || "Error al crear el usuario.");
      }
    } catch (err) {
      setFormError("Error de conexión con el servidor.");
      console.error(err);
    } finally {
      setFormLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  return (
    <div className="flex flex-1 flex-col bg-[#0d0e12] p-8 overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-8 animate-fade-in">
        
        {/* Title */}
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Users size={24} className="text-accent" />
            <span>👥 Administración de Usuarios</span>
          </h2>
          <p className="mt-1 text-sm text-gray-400">
            Control de cuentas registradas y asignación de permisos administrativos del sistema.
          </p>
        </div>

        {/* Form and list grid */}
        <div className="grid gap-8 md:grid-cols-3">
          
          {/* Create User Panel */}
          <div className="md:col-span-1 rounded-xl border border-border bg-sidebar p-6 shadow-lg h-fit">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-4 flex items-center space-x-2">
              <UserPlus size={16} />
              <span>Registrar Usuario</span>
            </h3>
            
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Correo electrónico
                </label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-[#0d0e12] px-3.5 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-accent"
                  placeholder="usuario@us.es"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Contraseña
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-[#0d0e12] px-3.5 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-accent"
                  placeholder="••••••••"
                  required
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="isAdminCheckbox"
                  checked={newIsAdmin}
                  onChange={(e) => setNewIsAdmin(e.target.checked)}
                  className="rounded border-border bg-[#0d0e12] text-accent focus:ring-accent"
                />
                <label htmlFor="isAdminCheckbox" className="text-xs font-semibold text-gray-300 cursor-pointer">
                  Hacer Administrador
                </label>
              </div>

              {formError && (
                <div className="flex items-center space-x-1.5 rounded-lg bg-red-500/10 border border-red-500/20 p-2.5 text-[11px] text-red-400">
                  <AlertCircle size={12} />
                  <span>{formError}</span>
                </div>
              )}

              {formSuccess && (
                <div className="flex items-center space-x-1.5 rounded-lg bg-green-500/10 border border-green-500/20 p-2.5 text-[11px] text-green-400">
                  <CheckCircle size={12} />
                  <span>{formSuccess}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={formLoading}
                className="w-full rounded-lg bg-accent py-2.5 text-xs font-semibold text-white shadow hover:bg-accent-hover transition-all"
              >
                {formLoading ? "Registrando..." : "Registrar Cuenta"}
              </button>
            </form>
          </div>

          {/* User List Panel */}
          <div className="md:col-span-2 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 px-1">
              Usuarios Registrados
            </h3>

            {error && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-400">
                {error}
              </div>
            )}

            {users.length === 0 && !loading && !error ? (
              <div className="rounded-xl border border-border bg-sidebar p-8 text-center text-gray-500">
                Cargando listado...
              </div>
            ) : (
              <div className="grid gap-3">
                {users.map((u) => {
                  const isSelf = u.email === currentUserEmail;
                  const dateStr = u.fecha_creacion
                    ? new Date(u.fecha_creacion).toLocaleDateString("es-ES", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "";

                  return (
                    <div
                      key={u.id}
                      className="flex items-center justify-between rounded-xl border border-border bg-sidebar px-5 py-4 shadow-sm"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center space-x-2">
                          <h4 className="truncate text-sm font-semibold text-white" title={u.email}>
                            {u.email}
                          </h4>
                          {isSelf && (
                            <span className="rounded bg-accent/10 px-1.5 py-0.5 text-[10px] font-bold text-accent">
                              Tú
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-400 mt-1">
                          {u.is_admin ? "🛡️ Administrador" : "👤 Usuario estándar"} • Creado: {dateStr}
                        </p>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleToggleAdmin(u.id, u.email, u.is_admin)}
                          disabled={isSelf}
                          className={`rounded-lg border border-border px-3 py-1.5 text-xs font-semibold transition-all ${
                            isSelf
                              ? "opacity-30 cursor-not-allowed text-gray-600"
                              : u.is_admin
                              ? "bg-[#0d0e12] text-gray-300 hover:text-white"
                              : "bg-[#0d0e12] text-accent hover:bg-accent hover:text-white"
                          }`}
                        >
                          {u.is_admin ? "Quitar Admin" : "Hacer Admin"}
                        </button>
                        
                        <button
                          onClick={() => confirmDeleteUser(u.id, u.email)}
                          disabled={isSelf}
                          className={`rounded-lg border border-border bg-[#0d0e12] p-2 text-accent transition-all ${
                            isSelf
                              ? "opacity-30 cursor-not-allowed text-gray-600 border-gray-800"
                              : "hover:bg-accent hover:text-white"
                          }`}
                          title="Eliminar usuario"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

      </div>

      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setUserToDelete(null);
        }}
        onConfirm={() => {
          if (userToDelete) {
            handleDeleteUser(userToDelete.id);
          }
        }}
        title="Eliminar cuenta de usuario"
        message={`¿Estás seguro de que deseas eliminar permanentemente la cuenta de '${userToDelete?.email}'? Se borrará todo su historial y accesos.`}
        confirmText="Eliminar"
        isDestructive={true}
      />
    </div>
  );
}
