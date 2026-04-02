"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ArchivedRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/artifacts");
  }, [router]);
  return null;
}
