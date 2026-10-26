import { useState } from "react";
import { api, setToken } from "./api";

// TEMPORARY: signs in as the shared test user so the goals screen can be tried.
// Delete this file when the real login screen is added.
const TEST_USER = {
  name: "TT01 Tester",
  email: "tt01-tester@example.com",
  password: "test-password-123",
};

export default function DevLogin({ onDone }: { onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signIn() {
    setBusy(true);
    setError(null);
    try {
      try {
        await api("/auth/register", { method: "POST", body: TEST_USER });
      } catch (e) {
        if ((e as { status?: number }).status !== 409) throw e;
      }
      const login = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: { email: TEST_USER.email, password: TEST_USER.password },
      });
      setToken(login.access_token);
      onDone();
    } catch {
      setError("Could not sign in. Check that the backend is reachable.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ padding: "2rem" }}>
      <p>Temporary sign-in for testing the savings goals screen.</p>
      <button onClick={signIn} disabled={busy}>
        {busy ? "Signing in..." : "Sign in as test user"}
      </button>
      {error && <p>{error}</p>}
    </div>
  );
}
