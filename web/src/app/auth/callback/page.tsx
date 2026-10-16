"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TbAlertTriangle, TbLoader2 } from "react-icons/tb";
import { supabase, useAuth } from "@/context/AuthContext";
import { Surface3D } from "@/components/three";
import styles from "@/app/page.module.css";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { openAuthModal } = useAuth();
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

    const routeUserByRole = async (token?: string) => {
      if (redirected) return;
      redirected = true;
      // Keep the spinner until router.replace() navigates away (clearing it here flashed the error card)
      let target = "/dashboard";
      if (token) {
        try {
          const res = await fetch("/api/v1/auth/me", {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok) {
            const profile = await res.json();
            if (profile.is_admin || profile.role === "admin") {
              target = "/admin";
            }
          }
        } catch {
          // fallback to /dashboard
        }
      }
      router.replace(target);
    };

    // 2. Active auth listener to capture SIGNED_IN or USER_UPDATED events
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      if (session && !redirected) {
        routeUserByRole(session.access_token);
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
          routeUserByRole(data.session.access_token);
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

  const pending = isProcessing && !errorMessage;

  return (
    <div className={`page-shell ${styles.callbackPage}`}>
      <Surface3D
        as="section"
        pad="lg"
        accent={pending ? "info" : "danger"}
        className={`${styles.callbackCard} enter-3d`}
        aria-live="polite"
        aria-busy={pending}
      >
        {pending ? (
          <>
            <span className="icon-well icon-well--lg">
              <TbLoader2 size={24} className="pulse" />
            </span>
            <h1 className={styles.callbackTitle}>Verifying Authentication</h1>
            <p className={styles.callbackText}>
              Completing secure session exchange and loading your QA dashboard...
            </p>
          </>
        ) : (
          <>
            <span className="icon-well icon-well--lg icon-well--solid">
              <TbAlertTriangle size={24} />
            </span>
            <h1 className={styles.callbackTitle}>Sign-In Incomplete</h1>
            <p className={`surface-inset ${styles.callbackError}`}>{errorMessage}</p>
            <div className={styles.callbackActions}>
              <button type="button" onClick={() => router.replace("/")} className="btn btn-secondary">
                Go to Home
              </button>
              <button
                type="button"
                onClick={() => {
                  router.replace("/");
                  openAuthModal("signin");
                }}
                className="btn btn-primary"
              >
                Try Sign In Again
              </button>
            </div>
          </>
        )}
      </Surface3D>
    </div>
  );
}
