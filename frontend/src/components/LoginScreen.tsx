import React, { useState } from "react";
import Cookies from "js-cookie";
import { API_URL } from "@/utils/api";

interface LoginProps {
  onLoginSuccess: (isAdmin: boolean, email: string) => void;
}


export function LoginScreen({ onLoginSuccess }: LoginProps) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    if (!email || !password) {
      setError("Por favor, rellene todos los campos.");
      setLoading(false);
      return;
    }

    try {
      if (isRegister) {
        // Register flow
        const res = await fetch(`${API_URL}/registro`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        const data = await res.json();
        if (res.ok) {
          setSuccess("Registro completado. Ya puedes iniciar sesión.");
          setIsRegister(false);
          setPassword("");
        } else {
          setError(data.detail || "Error al registrar el usuario.");
        }
      } else {
        // Login flow
        const params = new URLSearchParams();
        params.append("username", email);
        params.append("password", password);

        const res = await fetch(`${API_URL}/login`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: params,
        });

        const data = await res.json();
        if (res.ok) {
          const token = data.access_token;
          const isAdmin = data.is_admin || false;

          // Set cookies
          Cookies.set("auth_token", token, { expires: 7 });
          Cookies.set("is_admin", isAdmin ? "true" : "false", { expires: 7 });

          onLoginSuccess(isAdmin, email);
        } else {
          setError("Correo o contraseña incorrectos.");
        }
      }
    } catch (err) {
      setError("Error de conexión con el servidor.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#090a0c] px-4">
      <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-border bg-sidebar p-8 shadow-2xl animate-fade-in">
        {/* Glow effect */}
        <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-accent/20 blur-3xl"></div>
        <div className="absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-blue-500/10 blur-3xl"></div>

        <div className="flex flex-col items-center">
          <img
            src="https://www.uco.es/investigacion/proyectos/SEBASENet/images/thumb/Logo_US.png/655px-Logo_US.png"
            alt="Logo US"
            className="mb-4 h-16 w-auto object-contain filter brightness-110"
          />
          <h2 className="text-2xl font-bold tracking-tight text-white">
            Asistente Académico
          </h2>
          <p className="mt-1 text-sm text-gray-400">
            Universidad de Sevilla
          </p>
        </div>

        {/* Tab switch */}
        <div className="mt-8 flex rounded-lg bg-[#0d0e12] p-1 border border-border">
          <button
            type="button"
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
              !isRegister ? "bg-accent text-white" : "text-gray-400 hover:text-white"
            }`}
            onClick={() => {
              setIsRegister(false);
              setError("");
              setSuccess("");
            }}
          >
            Iniciar Sesión
          </button>
          <button
            type="button"
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
              isRegister ? "bg-accent text-white" : "text-gray-400 hover:text-white"
            }`}
            onClick={() => {
              setIsRegister(true);
              setError("");
              setSuccess("");
            }}
          >
            Registrarse
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">
              Correo electrónico
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-[#0d0e12] px-4 py-3 text-sm text-white placeholder-gray-500 transition-all focus:border-accent focus:outline-none"
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-[#0d0e12] px-4 py-3 text-sm text-white placeholder-gray-500 transition-all focus:border-accent focus:outline-none"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-400">
              {error}
            </div>
          )}

          {success && (
            <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-3 text-xs text-green-400">
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-lg bg-accent py-3 text-sm font-semibold text-white shadow-lg transition-all hover:bg-accent-hover active:scale-[0.98] disabled:opacity-50"
          >
            {loading ? "Procesando..." : isRegister ? "Registrar cuenta" : "Iniciar Sesión"}
          </button>
        </form>
      </div>
    </div>
  );
}
