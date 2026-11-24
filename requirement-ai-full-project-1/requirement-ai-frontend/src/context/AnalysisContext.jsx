import React, { createContext, useContext, useMemo, useState } from "react";

import {
  clearStoredAnalysis,
  getStoredAnalysis,
  storeAnalysis,
} from "../utils/analysisStorage";

const AnalysisContext = createContext(null);

export function AnalysisProvider({ children }) {
  const [analysis, setAnalysis] = useState(() => getStoredAnalysis());

  const value = useMemo(
    () => ({
      analysis,
      saveAnalysis(data) {
        const saved = storeAnalysis(data);
        setAnalysis(saved);
        return saved;
      },
      clearAnalysis() {
        clearStoredAnalysis();
        setAnalysis(null);
      },
    }),
    [analysis],
  );

  return (
    <AnalysisContext.Provider value={value}>
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error("useAnalysis must be used inside AnalysisProvider");
  }
  return context;
}
