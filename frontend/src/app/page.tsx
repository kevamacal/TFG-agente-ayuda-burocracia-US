"use client";

import React, { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { LoginScreen } from "../components/LoginScreen";
import { Sidebar } from "../components/Sidebar";
import { ChatInterface } from "../components/ChatInterface";
import { DocumentList } from "../components/DocumentList";
import { UserManagement } from "../components/UserManagement";
import { FeedbackList } from "../components/FeedbackList";
import { useChat } from "../hooks/useChat";
import { API_URL } from "@/utils/api";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("chat");
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  const chat = useChat();

  useEffect(() => {
    // Detect initial theme
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light" || savedTheme === "dark") {
      setTheme(savedTheme);
      document.documentElement.classList.toggle("dark", savedTheme === "dark");
    } else {
      const prefersDark = globalThis.matchMedia(
        "(prefers-color-scheme: dark)",
      ).matches;
      const initialTheme = prefersDark ? "dark" : "light";
      setTheme(initialTheme);
      document.documentElement.classList.toggle("dark", prefersDark);
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    document.documentElement.classList.toggle("dark", newTheme === "dark");
  };

  const checkAuth = async () => {
    const token = Cookies.get("auth_token");
    const adminCookie = Cookies.get("is_admin");

    if (token) {
      setIsAuthenticated(true);
      setIsAdmin(adminCookie === "true");

      // Fetch /auth/me to get current email
      try {
        const res = await fetch(`${API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const userData = await res.json();
          setUserEmail(userData.email);
          setIsAdmin(userData.is_admin);
        } else {
          // If token is invalid, clear cookies
          handleLogout();
        }
      } catch (err) {
        console.error("Error verifying authentication token:", err);
      }
    } else {
      setIsAuthenticated(false);
    }
  };

  const handleLoginSuccess = (admin: boolean, email: string) => {
    setIsAuthenticated(true);
    setIsAdmin(admin);
    setUserEmail(email);
    setActiveTab("chat");
    // Reload chat conversations once authenticated
    setTimeout(() => {
      globalThis.location.reload();
    }, 100);
  };

  const handleLogout = () => {
    Cookies.remove("auth_token");
    Cookies.remove("is_admin");
    setIsAuthenticated(false);
    setIsAdmin(false);
    setUserEmail(null);
    chat.setActiveConversationId(null);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  // Loading state during auth check
  if (isAuthenticated === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#090a0c]">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-t-accent border-border"></div>
      </div>
    );
  }

  // Not authenticated view
  if (!isAuthenticated) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  // Authenticated Dashboard Layout
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-textMain font-sans">
      <Sidebar
        conversations={chat.conversations}
        activeConversationId={chat.activeConversationId}
        setActiveConversationId={chat.setActiveConversationId}
        createConversation={chat.createConversation}
        deleteConversation={chat.deleteConversation}
        renameConversation={chat.renameConversation}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isAdmin={isAdmin}
        userEmail={userEmail}
        onLogout={handleLogout}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <div className="flex flex-1 flex-col overflow-hidden min-h-0">
        {activeTab === "chat" && (
          <ChatInterface
            messages={chat.messages}
            isLoading={chat.isLoading}
            onSendMessage={chat.sendMessage}
            activeConversationId={chat.activeConversationId}
            onSubmitFeedback={chat.submitFeedback}
          />
        )}

        {activeTab === "documents" && <DocumentList isAdmin={isAdmin} />}

        {activeTab === "users" && isAdmin && (
          <UserManagement currentUserEmail={userEmail} />
        )}

        {activeTab === "feedback" && isAdmin && <FeedbackList />}
      </div>
    </div>
  );
}
