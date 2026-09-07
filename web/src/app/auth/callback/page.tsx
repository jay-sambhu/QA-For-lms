"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/context/AuthContext";

export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    if (!supabase) {
      router.replace("/dashboard");
      return;
    }

    supabase.auth.getSession().then(({ data, error }) => {
      if (!error && data.session) {
        router.replace("/dashboard");
      } else {
        router.replace("/");
      }
    });
  }, [router]);

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#0b0f19",
      color: "#94a3b8",
      fontFamily: "sans-serif"
    }}>
      <p>Completing authentication, please wait...</p>
    </div>
  );
}
