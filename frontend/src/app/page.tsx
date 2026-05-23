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

  const chat = useChat();

  const checkAuth = async () => {
    const token = Cookies.get("auth_token");
    const adminCookie = Cookies.get("is_admin");

    if (token) {
      setIsAuthenticated(true);
      setIsAdmin(adminCookie === "true");
      
      // Fetch /me to get current email
      try {
        const res = await fetch(`${API_URL}/me`, {
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
      window.location.reload();
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
    <div className="flex h-screen w-screen overflow-hidden bg-background">
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
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        {activeTab === "chat" && (
          <ChatInterface
            messages={chat.messages}
            isLoading={chat.isLoading}
            onSendMessage={chat.sendMessage}
            activeConversationId={chat.activeConversationId}
            onSubmitFeedback={chat.submitFeedback}
          />
        )}

        {activeTab === "documents" && (
          <DocumentList isAdmin={isAdmin} />
        )}

        {activeTab === "users" && isAdmin && (
          <UserManagement currentUserEmail={userEmail} />
        )}

        {activeTab === "feedback" && isAdmin && (
          <FeedbackList />
        )}
      </div>
    </div>
  );
}
