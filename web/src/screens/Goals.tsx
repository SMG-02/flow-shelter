import { useCallback, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api } from "../api";
import { useDashboard } from "../DashboardContext";
import "./Goals.css";

type Priority = "low" | "medium" | "high";

type Goal = {
  id: number;
  name: string;
  target_amount: string;
  saved_amount: string;
  target_date: string | null;
  priority: Priority;
};

type Draft = { savings_goals: Goal[] };
type View = "list" | "detail" | "form" | "contribution";

type FormValues = {
  name: string;
  target_amount: string;
  saved_amount: string;
  target_date: string | null;
  priority: Priority;
};

const num = (v: string | number) => Number(v) || 0;

const percent = (g: Goal) => {
  const target = num(g.target_amount);
  return target > 0
    ? Math.min(100, Math.round((num(g.saved_amount) / target) * 100))
    : 0;
};

// The backend replaces the whole goal list on every save, so we always send every goal.
const toPayload = (list: Goal[]) =>
  list.map((g) => ({
    name: g.name,
    target_amount: g.target_amount,
    saved_amount: g.saved_amount,
    target_date: g.target_date,
    priority: g.priority,
  }));

function errorText(e: unknown) {
  const status = (e as { status?: number } | null)?.status;
  if (status === 401 || status === 403) {
    return "Your session has ended. Please sign in again.";
  }
  if (status === 422) {
    return "Some details are not valid. Check the amounts and try again.";
  }
  return "Something went wrong. Please try again.";
}

function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>;
}

function Progress({ value }: { value: number }) {
  return (
    <div className="progress">
      <i style={{ width: `${Math.min(value, 100)}%` }} />
    </div>
  );
}

export default function GoalsPage() {
  const { data, error: dashError, refresh } = useDashboard();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [view, setView] = useState<View>("list");
  const [index, setIndex] = useState(0);
  const [editing, setEditing] = useState<Goal | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const money = (v: number) =>
    new Intl.NumberFormat("en-ZA", {
      style: "currency",
      currency: data?.currency ?? "ZAR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(v);

  const loadGoals = useCallback(async () => {
    try {
      const draft = await api<Draft>("/api/onboarding");
      setGoals(draft.savings_goals);
      setMessage(null);
    } catch (e) {
      setMessage(errorText(e));
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    loadGoals();
  }, [loadGoals]);

  async function save(next: Goal[]) {
    setBusy(true);
    setMessage(null);
    try {
      const draft = await api<Draft>("/api/onboarding", {
        method: "PATCH",
        body: { savings_goals: toPayload(next) },
      });
      setGoals(draft.savings_goals);
      await refresh(); // keeps the dashboard numbers in sync with the planner
      return true;
    } catch (e) {
      setMessage(errorText(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function saveGoal(values: FormValues) {
    const next = editing
      ? goals.map((g, i) => (i === index ? { ...g, ...values } : g))
      : [...goals, { id: 0, ...values }];
    const ok = await save(next);
    if (ok) setView(editing ? "detail" : "list");
  }

  async function addContribution(amount: number) {
    const next = goals.map((g, i) =>
      i === index
        ? { ...g, saved_amount: (num(g.saved_amount) + amount).toFixed(2) }
        : g
    );
    const ok = await save(next);
    if (ok) setView("detail");
  }

  const goal = goals[index] as Goal | undefined;
  const available = num(data?.available_now ?? 0);
  const goalAlerts = (data?.alerts ?? []).filter(
    (a) => a.type === "goal_reached" || a.type === "goal_due_soon"
  );

  const snapshot = data && (
    <div className="fsg-snapshot">
      <Card>
        <small>AVAILABLE NOW</small>
        <h2>{money(available)}</h2>
        <p>Confirmed money you can use today</p>
      </Card>
      <Card>
        <small>
          PROJECTED BALANCE{data.forecast_is_estimate ? " (ESTIMATE)" : ""}
        </small>
        <h2>{money(num(data.projected_balance))}</h2>
        <p>If expected income arrives</p>
      </Card>
    </div>
  );

  return (
    <div className="fsg">
      {message && <div className="notice warning">{message}</div>}
      {dashError && (
        <div className="notice warning">
          Could not load your dashboard numbers.{" "}
          <button onClick={refresh}>Try again</button>
        </div>
      )}

      {view === "list" && (
        <>
          <div className="page-title">
            <div>
              <h1>Savings goals</h1>
              <p>Track contributions manually. FlowShelter does not move money.</p>
            </div>
            <button
              className="btn"
              onClick={() => {
                setEditing(null);
                setView("form");
              }}
            >
              + Add goal
            </button>
          </div>

          {snapshot}

          {goalAlerts.map((a, i) => (
            <div className="notice" key={i}>
              {a.message}
            </div>
          ))}

          {!loaded && <p className="muted">Loading your goals&hellip;</p>}

          {loaded && goals.length === 0 && (
            <Card className="empty">
              <h3>No savings goals yet</h3>
              <p>Create a goal for tax, equipment or time off.</p>
              <button
                className="btn secondary"
                onClick={() => {
                  setEditing(null);
                  setView("form");
                }}
              >
                Create your first goal
              </button>
            </Card>
          )}

          {goals.map((g, i) => (
            <Card key={`${g.name}-${i}`} className="goal-card clickable">
              <div
                role="button"
                tabIndex={0}
                onClick={() => {
                  setIndex(i);
                  setView("detail");
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    setIndex(i);
                    setView("detail");
                  }
                }}
              >
                <div className="section-head">
                  <div>
                    <p className="eyebrow">SAVINGS GOAL</p>
                    <h2>{g.name}</h2>
                  </div>
                  <span className="status">
                    {percent(g) >= 100 ? "Reached" : "In progress"}
                  </span>
                </div>
                <Progress value={percent(g)} />
                <div className="three-stats">
                  <div>
                    <small>SAVED</small>
                    <b>{money(num(g.saved_amount))}</b>
                  </div>
                  <div>
                    <small>REMAINING</small>
                    <b>
                      {money(
                        Math.max(0, num(g.target_amount) - num(g.saved_amount))
                      )}
                    </b>
                  </div>
                  <div>
                    <small>TARGET</small>
                    <b>{money(num(g.target_amount))}</b>
                  </div>
                </div>
                {g.target_date && <p>Target date: {g.target_date}</p>}
              </div>
            </Card>
          ))}
        </>
      )}

      {view === "detail" && !goal && (
        <button className="back" onClick={() => setView("list")}>
          &larr; All goals
        </button>
      )}

      {view === "detail" && goal && (
        <>
          <button className="back" onClick={() => setView("list")}>
            &larr; All goals
          </button>
          <div className="page-title">
            <div>
              <p className="eyebrow">SAVINGS GOAL</p>
              <h1>{goal.name}</h1>
              <p>
                {goal.target_date
                  ? `Target date \u00b7 ${goal.target_date}`
                  : "No target date"}{" "}
                &middot; Priority: {goal.priority}
              </p>
            </div>
            <div className="actions">
              <button
                className="btn secondary"
                onClick={() => {
                  setEditing(goal);
                  setView("form");
                }}
              >
                Edit goal
              </button>
              <button className="btn" onClick={() => setView("contribution")}>
                + Add contribution
              </button>
            </div>
          </div>

          <Card>
            <Progress value={percent(goal)} />
            <div className="three-stats">
              <div>
                <small>SAVED</small>
                <h2>{money(num(goal.saved_amount))}</h2>
              </div>
              <div>
                <small>REMAINING</small>
                <h2>
                  {money(
                    Math.max(0, num(goal.target_amount) - num(goal.saved_amount))
                  )}
                </h2>
              </div>
              <div>
                <small>TARGET</small>
                <h2>{money(num(goal.target_amount))}</h2>
              </div>
            </div>
          </Card>

          {snapshot}

          {data &&
            num(goal.target_amount) - num(goal.saved_amount) > available && (
              <div className="notice">
                The remaining amount is more than the {money(available)} you
                have available right now.
              </div>
            )}

          <p className="muted">
            Contributions are records only. No funds are transferred by
            FlowShelter.
          </p>
        </>
      )}

      {view === "form" && (
        <GoalForm
          key={editing ? `edit-${index}` : "new"}
          goal={editing}
          busy={busy}
          onCancel={() => setView(editing ? "detail" : "list")}
          onSave={saveGoal}
        />
      )}

      {view === "contribution" && goal && (
        <Contribution
          goalName={goal.name}
          busy={busy}
          onCancel={() => setView("detail")}
          onSave={addContribution}
        />
      )}
    </div>
  );
}

function GoalForm({
  goal,
  busy,
  onCancel,
  onSave,
}: {
  goal: Goal | null;
  busy: boolean;
  onCancel: () => void;
  onSave: (v: FormValues) => void;
}) {
  const [name, setName] = useState(goal?.name ?? "");
  const [target, setTarget] = useState(goal?.target_amount ?? "");
  const [saved, setSaved] = useState(goal?.saved_amount ?? "0");
  const [date, setDate] = useState(goal?.target_date ?? "");
  const [priority, setPriority] = useState<Priority>(goal?.priority ?? "medium");
  const [error, setError] = useState<string | null>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    const t = Number(target);
    const s = Number(saved);
    if (!name.trim() || name.trim().length > 100) {
      setError("Enter a goal name (up to 100 characters).");
      return;
    }
    if (!(t > 0)) {
      setError("The target amount must be more than zero.");
      return;
    }
    if (!(s >= 0)) {
      setError("The saved amount cannot be negative.");
      return;
    }
    setError(null);
    onSave({
      name: name.trim(),
      target_amount: t.toFixed(2),
      saved_amount: s.toFixed(2),
      target_date: date || null,
      priority,
    });
  }

  return (
    <>
      <div className="page-title">
        <h1>{goal ? "Edit goal" : "Create a goal"}</h1>
      </div>
      <form onSubmit={submit}>
        <Card className="form-card">
          {error && <div className="notice warning">{error}</div>}
          <label className="field">
            <span>Goal name *</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Tax reserve"
              maxLength={100}
            />
          </label>
          <div className="form-grid">
            <label className="field">
              <span>Target amount *</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Already saved</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={saved}
                onChange={(e) => setSaved(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Target date (optional)</span>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Priority</span>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as Priority)}
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </label>
          </div>
          <div className="footer-actions">
            <button type="button" className="btn secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={busy}>
              {busy ? "Saving..." : "Save goal"}
            </button>
          </div>
        </Card>
      </form>
    </>
  );
}

function Contribution({
  goalName,
  busy,
  onCancel,
  onSave,
}: {
  goalName: string;
  busy: boolean;
  onCancel: () => void;
  onSave: (amount: number) => void;
}) {
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    const n = Number(amount);
    if (!(n > 0)) {
      setError("Enter an amount greater than zero.");
      return;
    }
    setError(null);
    onSave(n);
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>Add contribution</h1>
          <p>{goalName}</p>
        </div>
      </div>
      <form onSubmit={submit}>
        <Card className="form-card">
          {error && <div className="notice warning">{error}</div>}
          <label className="field">
            <span>Amount</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="e.g. 1000"
            />
          </label>
          <div className="notice">
            This records progress only. It does not transfer money.
          </div>
          <div className="footer-actions">
            <button type="button" className="btn secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={busy}>
              {busy ? "Saving..." : "Record contribution"}
            </button>
          </div>
        </Card>
      </form>
    </>
  );
}
