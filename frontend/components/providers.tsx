"use client";

import React, { createContext, useContext, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

interface InspectorState {
  title: string;
  content: React.ReactNode;
}

interface InspectorContextValue {
  inspector: InspectorState | null;
  openInspector: (title: string, content: React.ReactNode) => void;
  closeInspector: () => void;
}

const InspectorContext = createContext<InspectorContextValue>({
  inspector: null,
  openInspector: () => {},
  closeInspector: () => {},
});

export function useInspector() {
  return useContext(InspectorContext);
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  const [inspector, setInspector] = useState<InspectorState | null>(null);

  return (
    <QueryClientProvider client={queryClient}>
      <InspectorContext.Provider
        value={{
          inspector,
          openInspector: (title, content) => setInspector({ title, content }),
          closeInspector: () => setInspector(null),
        }}
      >
        {children}
      </InspectorContext.Provider>
    </QueryClientProvider>
  );
}
