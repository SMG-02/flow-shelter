import { useState } from "react";
import { api } from "./api";
import { useDashboard } from "./DashboardContext";

const inputStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  boxSizing: "border-box",
  padding: "11px",
  marginTop: "6px",
  marginBottom: "16px",
  border: "1px solid #cbd5e1",
  borderRadius: "8px",
  fontSize: "15px",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontWeight: 600,
  marginBottom: "4px",
};

type ApiError = Error & { status?: number; data?: unknown };

export default function FinancialHealthCheck() {
  const { data, loading, error, refresh } = useDashboard();
  const [workType, setWorkType] = useState("employed");
  const [incomePattern, setIncomePattern] = useState("fixed");
  const [income, setIncome] = useState("");
  const [balance, setBalance] = useState("");
  const [savings, setSavings] = useState("0");
  const [incomeSource, setIncomeSource] = useState("");
  const [incomeAmount, setIncomeAmount] = useState("");
  const [incomeDate, setIncomeDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [formError, setFormError] = useState("");

  const currency = data?.currency || "ZAR";
  const money = (value: string | number) =>
    new Intl.NumberFormat("en-ZA", {
      style: "currency",
      currency,
    }).format(Number(value) || 0);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setFormError("");

    try {
      const patch: Record<string, unknown> = {
        financial_profile: {
          work_type: workType,
          income_pattern: incomePattern,
          typical_income: Number(income),
          currency: "ZAR",
        },
        financial_balance: {
          available_balance: Number(balance),
          existing_savings: Number(savings || 0),
        },
      };

      // Only replace expected incomes when the user enters a complete one.
      // Omitting this field preserves any existing expected-income records.
      if (incomeSource.trim() && incomeAmount && incomeDate) {
        patch.expected_incomes = [{
          source: incomeSource.trim(),
          amount: Number(incomeAmount),
          expected_date: incomeDate,
        }];
      } else if (
        incomeSource.trim() ||
        incomeAmount ||
        incomeDate
      ) {
        throw new Error(
          "To add expected income, complete its source, amount and date."
        );
      }

      await api("/api/onboarding", {
        method: "PATCH",
        body: patch,
      });

      await refresh();
      setMessage("Your information was saved. Dashboard results have been refreshed.");
    } catch (e) {
      const err = e as ApiError;
      if (err.status === 401 || err.status === 403) {
        setFormError("Your session may have expired. Please sign in again.");
      } else if (err.status === 422) {
        setFormError("Some details were rejected. Check the amounts and date, then try again.");
      } else {
        setFormError(err.message || "Could not save your information. Check that the backend is running.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 850, margin: "0 auto", padding: "28px 18px", color: "#172033" }}>
      <header style={{ marginBottom: 24 }}>
        <p style={{ color: "#0f766e", fontWeight: 700, marginBottom: 6 }}>FLOWSHELTER</p>
        <h1 style={{ margin: "0 0 8px" }}>Financial health check</h1>
        <p style={{ color: "#64748b" }}>Plan for the days between paydays.</p>
      </header>

      <form onSubmit={submit} style={{ background: "#fff", padding: 22, border: "1px solid #e2e8f0", borderRadius: 14 }}>
        <h2 style={{ marginTop: 0 }}>Your financial details</h2>

        <label style={labelStyle}>Work type</label>
        <select value={workType} onChange={(e) => setWorkType(e.target.value)} style={inputStyle}>
          <option value="employed">Employed</option>
          <option value="self-employed">Self-employed</option>
          <option value="freelancer">Freelancer</option>
          <option value="student">Student</option>
          <option value="unemployed">Not currently employed</option>
          <option value="other">Other</option>
        </select>

        <label style={labelStyle}>Income pattern</label>
        <select value={incomePattern} onChange={(e) => setIncomePattern(e.target.value)} style={inputStyle}>
          <option value="fixed">Fixed income</option>
          <option value="irregular">Irregular income</option>
          <option value="mixed">A mix of fixed and irregular income</option>
        </select>

        <label style={labelStyle}>Typical income (ZAR)</label>
        <input required type="number" min="0" step="0.01" value={income} onChange={(e) => setIncome(e.target.value)} style={inputStyle} placeholder="e.g. 12000" />

        <label style={labelStyle}>Money available now (ZAR)</label>
        <input required type="number" min="0" step="0.01" value={balance} onChange={(e) => setBalance(e.target.value)} style={inputStyle} placeholder="e.g. 2500" />

        <label style={labelStyle}>Existing savings (ZAR)</label>
        <input required type="number" min="0" step="0.01" value={savings} onChange={(e) => setSavings(e.target.value)} style={inputStyle} />

        <h3>Expected income (optional)</h3>
        <p style={{ color: "#64748b", fontSize: 14 }}>Add a payment you expect to receive. Leave all three fields empty if you have none to add.</p>

        <label style={labelStyle}>Income source</label>
        <input value={incomeSource} onChange={(e) => setIncomeSource(e.target.value)} style={inputStyle} placeholder="e.g. Salary" />

        <label style={labelStyle}>Expected amount (ZAR)</label>
        <input type="number" min="0.01" step="0.01" value={incomeAmount} onChange={(e) => setIncomeAmount(e.target.value)} style={inputStyle} />

        <label style={labelStyle}>Expected payment date</label>
        <input type="date" value={incomeDate} onChange={(e) => setIncomeDate(e.target.value)} style={inputStyle} />

        {formError && <p role="alert" style={{ color: "#b91c1c" }}>{formError}</p>}
        {message && <p role="status" style={{ color: "#0f766e" }}>{message}</p>}

        <button type="submit" disabled={busy} style={{ background: "#0f766e", color: "#fff", border: 0, borderRadius: 8, padding: "12px 18px", fontWeight: 700, cursor: busy ? "wait" : "pointer" }}>
          {busy ? "Saving and updating..." : "Calculate my financial health"}
        </button>
      </form>

      <section style={{ marginTop: 28 }}>
        <h2>Your dashboard</h2>
        {loading && <p>Loading your latest financial results...</p>}
        {!loading && error && (
          <p role="alert" style={{ color: "#b91c1c" }}>
            {error}. Submit your details to save them and retry the dashboard.
          </p>
        )}

        {data && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 14 }}>
              {[
                ["Available now", data.available_now],
                ["Projected balance", data.projected_balance],
                ["Essential commitments", data.essential_commitments],
              ].map(([title, amount]) => (
                <article key={title} style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 18 }}>
                  <p style={{ color: "#64748b", marginTop: 0 }}>{title}</p>
                  <strong style={{ fontSize: 22 }}>{money(amount)}</strong>
                </article>
              ))}
            </div>

            <p style={{ color: "#64748b", fontSize: 13 }}>
              {data.forecast_is_estimate
                ? "Projection is an estimate based on the information currently recorded."
                : "Projection returned by the backend."}
            </p>

            <h3>Financial alerts</h3>
            {data.alerts.length === 0 ? (
              <p>No alerts returned by the backend.</p>
            ) : (
              <ul>
                {data.alerts.map((alert, index) => (
                  <li key={`${alert.type}-${index}`} style={{ marginBottom: 10 }}>
                    <strong>{alert.severity.toUpperCase()}:</strong> {alert.message}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>
    </main>
  );
}
