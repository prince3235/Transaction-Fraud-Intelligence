"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Sidebar, type PageKey } from "@/components/fraud/sidebar";
import { Topbar } from "@/components/fraud/topbar";
import { CommandCenterPage } from "@/components/fraud/pages/command-center";
import { AlertsPage } from "@/components/fraud/pages/alerts";
import { CasesPage } from "@/components/fraud/pages/cases";
import { SimulationPage } from "@/components/fraud/pages/simulation";
import { RulesPage } from "@/components/fraud/pages/rules";
import { ModelRegistryPage } from "@/components/fraud/pages/model-registry";
import { AuditPage } from "@/components/fraud/pages/audit";
import { LoginPage } from "@/components/fraud/pages/login";

export default function Home() {
  const { user, loading, login, logout } = useAuth();
  const [page, setPage] = useState<PageKey>("command-center");

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </div>
    );
  }

  if (!user) {
    return (
      <LoginPage
        onLogin={async (u) => {
          await login(u.name, "demo-password", u.role);
        }}
      />
    );
  }

  const roleLabel =
    user.role === "Admin" ? "Admin" :
    user.role === "Fraud_Analyst" ? "Fraud Analyst" :
    user.role === "Compliance_Officer" ? "Compliance Officer" :
    user.role === "Auditor" ? "Auditor" :
    user.role;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar
        active={page}
        onNavigate={setPage}
        user={{ name: user.username, role: roleLabel }}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar page={page} />
        <main className="scroll-thin flex-1 overflow-y-auto p-6">
          {page === "command-center" && <CommandCenterPage />}
          {page === "alerts" && <AlertsPage />}
          {page === "cases" && <CasesPage />}
          {page === "simulation" && <SimulationPage />}
          {page === "rules" && <RulesPage />}
          {page === "model-registry" && <ModelRegistryPage />}
          {page === "audit" && <AuditPage />}
        </main>
      </div>
    </div>
  );
}
