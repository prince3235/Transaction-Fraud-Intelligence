"use client"

import { DataTable } from "@/components/shared/DataTable"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/client"
import { useRouter } from "next/navigation"

export default function CasesPage() {
  const router = useRouter()
  
  const { data: alerts, isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(1),
    initialData: []
  })

  return (
    <div className="space-y-6">
      <h2 className="font-display text-xl font-medium text-mist">Cases</h2>
      <DataTable 
        data={alerts || []}
        isLoading={isLoading}
        onRowClick={(item) => router.push(`/cases/case-${item.id}`)}
        emptyStateTitle="No Cases"
        emptyStateDescription="There are no active cases assigned to you or waiting in the queue."
        columns={[
          { 
            header: "Case ID", 
            cell: (item) => <span className="font-mono text-sm text-signal">case-{item.id}</span>
          },
          { 
            header: "Txn ID", 
            accessorKey: "transaction_id",
            className: "font-mono text-sm text-mist/80"
          },
          { 
            header: "Status",
            cell: (item) => <span className="text-sm">OPEN</span>
          },
          { 
            header: "Created",
            cell: (item) => <span className="font-mono text-xs text-mist/60">{new Date(item.timestamp).toLocaleString()}</span>
          }
        ]}
      />
    </div>
  )
}
