"use client"

import { DataTable } from "@/components/shared/DataTable"
import { OpaquePanel } from "@/components/shared/OpaquePanel"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import { useRole } from "@/store"

const mockRules = [
  { id: "rule-1", name: "High Velocity IP", condition_json: '{"field":"velocity_10m","operator":">","value":5}', action: "FLAG", active: true, created_at: "2026-07-06" },
  { id: "rule-2", name: "Large Amount Offline", condition_json: '{"field":"amount","operator":">","value":10000}', action: "BLOCK", active: false, created_at: "2026-07-05" },
]

export default function BusinessRulesPage() {
  const role = useRole()
  const [rules, setRules] = useState(mockRules)

  if (role !== "Admin/Executive") {
    return <div className="p-12 text-center text-ember font-medium">Access Denied: Admin/Executive role required.</div>
  }

  return (
    <div className="space-y-6">
      <h2 className="font-display text-xl font-medium text-mist">Business Rules Engine</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <DataTable 
            data={rules}
            columns={[
              { header: "Rule Name", accessorKey: "name", className: "font-medium" },
              { header: "Condition (Internal)", cell: (item) => <code className="text-[10px] bg-abyss/50 px-1 py-0.5 rounded text-mist/60">{item.condition_json}</code> },
              { header: "Action", cell: (item) => <span className={`text-xs px-2 py-1 rounded ${item.action === 'BLOCK' ? 'bg-ember/20 text-text-on-ember' : 'bg-signal/20 text-signal'}`}>{item.action}</span> },
              { header: "Status", cell: (item) => (
                <span className={`text-xs ${item.active ? 'text-signal' : 'text-mist/40'}`}>
                  {item.active ? 'Active' : 'Inactive'}
                </span>
              )}
            ]}
          />
        </div>

        <div className="lg:col-span-1">
          <OpaquePanel className="p-6 sticky top-24">
            <h3 className="font-display text-lg font-medium text-mist mb-4">Create Rule</h3>
            <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
              <div className="space-y-1.5">
                <label className="text-xs text-mist/70 uppercase">Rule Name</label>
                <input type="text" className="w-full bg-abyss border border-mist/20 rounded p-2 text-sm text-mist focus:border-signal outline-none" placeholder="e.g. Block High Velocity" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-mist/70 uppercase">Field</label>
                <select className="w-full bg-abyss border border-mist/20 rounded p-2 text-sm text-mist focus:border-signal outline-none">
                  <option value="amount">Transaction Amount</option>
                  <option value="velocity_10m">Velocity (10m)</option>
                  <option value="ip_risk">IP Risk Score</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs text-mist/70 uppercase">Operator</label>
                  <select className="w-full bg-abyss border border-mist/20 rounded p-2 text-sm text-mist focus:border-signal outline-none">
                    <option value=">">&gt; (Greater than)</option>
                    <option value="<">&lt; (Less than)</option>
                    <option value="==">== (Equals)</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs text-mist/70 uppercase">Value</label>
                  <input type="number" className="w-full bg-abyss border border-mist/20 rounded p-2 text-sm text-mist font-mono focus:border-signal outline-none" placeholder="0.0" />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-mist/70 uppercase">Action</label>
                <select className="w-full bg-abyss border border-mist/20 rounded p-2 text-sm text-mist focus:border-signal outline-none">
                  <option value="FLAG">Flag for Review</option>
                  <option value="BLOCK">Block Transaction</option>
                </select>
              </div>
              <Button type="submit" className="w-full bg-signal text-[var(--text-on-signal)] hover:bg-signal/80 mt-2">
                Add Rule
              </Button>
            </form>
          </OpaquePanel>
        </div>
      </div>
    </div>
  )
}
