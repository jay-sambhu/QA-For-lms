"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/context/AuthContext";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    if (!supabase) {
      setErrorMessage("Authentication client is not configured on this deployment.");
      setIsProcessing(false);
      return;
    }

    // 1. Inspect URL search params and hash fragment for OAuth errors
    if (typeof window !== "undefined") {
      const searchParams = new URLSearchParams(window.location.search);
      const hash = window.location.hash.startsWith("#") ? window.location.hash.substring(1) : window.location.hash;
      const hashParams = new URLSearchParams(hash);

      const error = searchParams.get("error") || hashParams.get("error");
      const errorDesc =
        searchParams.get("error_description") ||
        hashParams.get("error_description") ||
        searchParams.get("message") ||
        hashParams.get("message");

      if (error || errorDesc) {
        setErrorMessage(
          errorDesc
            ? decodeURIComponent(errorDesc.replace(/\+/g, " "))
            : `Authentication failed (${error || "unknown error"}). Please verify your domain configuration.`
        );
        setIsProcessing(false);
        return;
      }
    }

    let redirected = false;

    // 2. Active auth listener to capture SIGNED_IN or USER_UPDATED events
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      if (session && !redirected) {
        redirected = true;
        setIsProcessing(false);
        router.replace("/dashboard");
      }
    });

    // 3. Check existing session / trigger token exchange
    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (error) {
          setErrorMessage(error.message);
          setIsProcessing(false);
          return;
        }
        if (data.session && !redirected) {
          redirected = true;
          setIsProcessing(false);
          router.replace("/dashboard");
        }
      })
      .catch((err) => {
        setErrorMessage(err instanceof Error ? err.message : "Failed to verify session.");
        setIsProcessing(false);
      });

    // 4. Sane timeout grace period (4.5s) for token hydration
    const timeout = setTimeout(() => {
      if (!redirected) {
        setIsProcessing(false);
        setErrorMessage(
          "Authentication timed out or session token could not be hydrated. This typically occurs if the callback URL is not listed in Supabase Allowed Redirect URLs."
        );
      }
    }, 4500);

    return () => {
      clearTimeout(timeout);
      authListener?.subscription?.unsubscribe();
    };
  }, [router]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#080c14",
        color: "#f8fafc",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        padding: "20px",
      }}
    >
      <div
        style={{
          maxWidth: "460px",
          width: "100%",
          padding: "36px 32px",
          background: "rgba(15, 23, 42, 0.8)",
          borderRadius: "16px",
          border: errorMessage ? "1px solid rgba(239, 68, 68, 0.4)" : "1px solid rgba(56, 189, 248, 0.2)",
          boxShadow: errorMessage
            ? "0 20px 40px -15px rgba(239, 68, 68, 0.15)"
            : "0 20px 40px -15px rgba(56, 189, 248, 0.15)",
          textAlign: "center",
          backdropFilter: "blur(12px)",
        }}
      >
        {isProcessing && !errorMessage ? (
          <>
            <div
              style={{
                width: "44px",
                height: "44px",
                margin: "0 auto 20px",
                border: "3px solid rgba(56, 189, 248, 0.2)",
                borderTopColor: "#38bdf8",
                borderRadius: "50%",
                animation: "spin 1s linear infinite",
              }}
            />
            <h2 style={{ fontSize: "1.25rem", fontWeight: 600, margin: "0 0 8px" }}>
              Verifying Authentication
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "0.9rem", margin: 0 }}>
              Completing secure session exchange and loading your QA dashboard...
            </p>
            <style>{`
              @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
              }
            `}</style>
          </>
        ) : (
          <>
            <div
              style={{
                width: "48px",
                height: "48px",
                margin: "0 auto 16px",
                borderRadius: "50%",
                background: "rgba(239, 68, 68, 0.15)",
                color: "#ef4444",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "24px",
                fontWeight: "bold",
              }}
            >
              !
            </div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 600, margin: "0 0 8px", color: "#f87171" }}>
              Sign-In Incomplete
            </h2>
            <p
              style={{
                color: "#cbd5e1",
                fontSize: "0.875rem",
                lineHeight: 1.5,
                margin: "0 0 24px",
                background: "rgba(15, 23, 42, 0.6)",
                padding: "12px 14px",
                borderRadius: "8px",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                textAlign: "left",
                wordBreak: "break-word",
              }}
            >
              {errorMessage}
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
              <button
                type="button"
                onClick={() => router.replace("/")}
                style={{
                  padding: "10px 18px",
                  borderRadius: "8px",
                  background: "#1e293b",
                  color: "#94a3b8",
                  border: "1px solid rgba(148, 163, 184, 0.2)",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Go to Home
              </button>
              <button
                type="button"
                onClick={() => router.replace("/?auth=signin")}
                style={{
                  padding: "10px 18px",
                  borderRadius: "8px",
                  background: "linear-gradient(135deg, #0284c7, #2563eb)",
                  color: "#ffffff",
                  border: "none",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Try Sign In Again
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
