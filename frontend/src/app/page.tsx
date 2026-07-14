"use client";

import { useState } from "react";
import { LoginPage } from "@/components/fraud/pages/login";
import { Sidebar, type PageKey } from "@/components/fraud/sidebar";
import { Topbar } from "@/components/fraud/topbar";
import { CommandCenterPage } from "@/components/fraud/pages/command-center";
import { AlertsPage } from "@/components/fraud/pages/alerts";
import { CasesPage } from "@/components/fraud/pages/cases";
import { SimulationPage } from "@/components/fraud/pages/simulation";
import { RulesPage } from "@/components/fraud/pages/rules";
import { ModelRegistryPage } from "@/components/fraud/pages/model-registry";
import { AuditPage } from "@/components/fraud/pages/audit";

interface User {
  name: string;
  role: string;
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [page, setPage] = useState<PageKey>("command-center");

  if (!user) {
    return <LoginPage onLogin={setUser} />;
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
        user={{ name: user.name, role: roleLabel }}
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
