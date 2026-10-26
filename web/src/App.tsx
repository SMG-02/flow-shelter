
import { useState } from "react";
import "./App.css";
import DevLogin from "./DevLogin";
import FinancialHealthCheck from "./FinancialHealthCheck";
import { DashboardProvider } from "./DashboardContext";
import Welcome from "./components/Welcom";

function App() {
  const [signedIn, setSignedIn] = useState(false);
  const [showHealthCheck, setShowHealthCheck] = useState(false);

  if (!signedIn) {
    return (
      <>
        <Welcome
          teamName="NewTech"
          appName="FlowShelter"
          slogan="Plan for the days between paydays"
        />
        <div style={{ textAlign: "center", padding: "1rem" }}>
          <DevLogin onDone={() => setSignedIn(true)} />
        </div>
      </>
    );
  }

  return (
    <DashboardProvider>
      <nav
        aria-label="Main navigation"
        style={{
          display: "flex",
          justifyContent: "center",
          gap: 10,
          padding: 16,
          background: "#f8fafc",
          borderBottom: "1px solid #e2e8f0",
        }}
      >
        <button
          type="button"
          onClick={() => setShowHealthCheck((current) => !current)}
        >
          {showHealthCheck ? "Welcome" : "Financial health check"}
        </button>
      </nav>

      {showHealthCheck ? (
        <FinancialHealthCheck />
      ) : (
        <Welcome
          teamName="NewTech"
          appName="FlowShelter"
          slogan="Plan for the days between paydays"
        />
      )}
    </DashboardProvider>
  );
}

export default App;