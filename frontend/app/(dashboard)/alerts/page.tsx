"use client"

import { DataTable } from "@/components/shared/DataTable"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { SonarPulse } from "@/components/shared/SonarPulse"
import { Button } from "@/components/ui/button"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/client"
import { useRouter } from "next/navigation"
import { useRole } from "@/store"
import { useEffect, useState } from "react"
import { PredictionLog } from "@/types"

export default function AlertsPage() {
  const router = useRouter()
  const role = useRole()
  
  const { data: alerts, isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(1),
    initialData: []
  })

  // To track new alerts for SonarPulse
  const [knownIds, setKnownIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (alerts && alerts.length > 0) {
      if (knownIds.size === 0) {
        // Initial load, mark all as known so they don't pulse
        setKnownIds(new Set(alerts.map(a => a.id)))
      } else {
        // Update known IDs, any new ones will trigger pulse during render
        setKnownIds(prev => {
          const updated = new Set(prev)
          alerts.forEach(a => updated.add(a.id))
          return updated
        })
      }
    }
  }, [alerts])

  const canBulkAssign = role === "Senior Analyst" || role === "Admin/Executive"

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-medium text-mist">Live Alerts</h2>
        <div className="flex gap-3">
          {/* Mock filters */}
          <select className="bg-trench border border-mist/20 rounded-md px-3 py-1.5 text-sm text-mist focus:outline-none focus:border-signal">
            <option>All Risk Levels</option>
            <option>High Risk</option>
            <option>Medium Risk</option>
          </select>
          {canBulkAssign && (
            <Button variant="outline" className="border-mist/20 text-mist hover:bg-mist/10">
              Bulk Assign
            </Button>
          )}
        </div>
      </div>

      <DataTable 
        data={alerts || []}
        isLoading={isLoading}
        onRowClick={(item) => router.push(`/cases/case-${item.id}`)}
        columns={[
          { 
            header: "Risk",
            cell: (item) => {
              const isNew = !knownIds.has(item.id) && knownIds.size > 0;
              return (
                <SonarPulse trigger={isNew} color={item.risk_level === 'high' ? 'ember' : 'signal'}>
                  <RiskBadge level={item.risk_level} />
                </SonarPulse>
              )
            }
          },
          { 
            header: "Txn ID", 
            accessorKey: "transaction_id",
            className: "font-mono text-sm text-mist/80"
          },
          { 
            header: "Amount",
            cell: (item) => <span className="font-mono text-sm">${item.amount.toFixed(2)}</span>
          },
          { 
            header: "Probability",
            cell: (item) => <span className="font-mono text-sm text-mist/60">{(item.fraud_probability * 100).toFixed(1)}%</span>
          },
          { 
            header: "Time",
            cell: (item) => <span className="font-mono text-xs text-mist/40">{new Date(item.timestamp).toLocaleTimeString()}</span>
          }
        ]}
      />
    </div>
  )
}
