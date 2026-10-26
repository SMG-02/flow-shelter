import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";

export type SavingsGoal = {
  id: number;
  name: string;
  target_amount: string;
  saved_amount: string;
  progress_percentage: number;
};

export type Dashboard = {
  currency: string;
  available_now: string;
  projected_balance: string;
  essential_commitments: string;
  savings_goals: SavingsGoal[];
  alerts: { type: string; severity: string; message: string }[];
  forecast_is_estimate: boolean;
};

type DashboardState = {
  data: Dashboard | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const DashboardContext = createContext<DashboardState | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api<Dashboard>("/api/dashboard/overview"));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <DashboardContext.Provider value={{ data, loading, error, refresh }}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used inside DashboardProvider");
  return ctx;
}
