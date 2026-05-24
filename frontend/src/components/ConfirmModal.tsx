import React from "react";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDestructive?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  isDestructive = true,
}: ConfirmModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
      />
      
      {/* Modal Container */}
      <div className="relative w-full max-w-md transform overflow-hidden rounded-2xl border border-border bg-cardLighter p-6 shadow-2xl transition-all duration-300 animate-fade-in">
        
        {/* Close Button (X) */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1 text-textMuted hover:bg-hover hover:text-textMain transition-all"
        >
          <X size={18} />
        </button>

        {/* Content */}
        <div className="flex items-start space-x-4">
          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${
            isDestructive ? "bg-red-500/10 text-red-500" : "bg-accent/10 text-accent"
          }`}>
            <AlertTriangle size={24} />
          </div>
          
          <div className="flex-1">
            <h3 className="text-lg font-bold text-textMain leading-6">
              {title}
            </h3>
            <p className="mt-2 text-sm text-textMuted leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-border px-4 py-2.5 text-sm font-semibold text-textMuted hover:bg-hover hover:text-textMain transition-all focus:outline-none"
          >
            {cancelText}
          </button>
          
          <button
            type="button"
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`rounded-xl px-5 py-2.5 text-sm font-semibold text-white shadow-lg transition-all focus:outline-none ${
              isDestructive
                ? "bg-red-600 hover:bg-red-500 active:scale-95"
                : "bg-accent hover:bg-accent-hover active:scale-95"
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
