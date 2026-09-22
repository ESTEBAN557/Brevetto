"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getTokens } from "@/lib/auth";

/** Redirige a /login si no hay sesión. Devuelve el usuario cuando está listo. */
export function useAuthGuard(): { ready: boolean; username: string | null } {
  const router = useRouter();
  const [state, setState] = useState<{ ready: boolean; username: string | null }>({
    ready: false,
    username: null,
  });

  useEffect(() => {
    const tokens = getTokens();
    if (!tokens) {
      router.replace("/login");
      return;
    }
    setState({ ready: true, username: tokens.username });
  }, [router]);

  return state;
}
