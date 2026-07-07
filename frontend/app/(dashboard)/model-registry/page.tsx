"use client"

import { DataTable } from "@/components/shared/DataTable"
import { OpaquePanel } from "@/components/shared/OpaquePanel"
import { Button } from "@/components/ui/button"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useState } from "react"

// Mock Data
const runs = [
  { id: "run-v3.1", metrics: { roc_auc: 0.94 }, stage: "Production", time: "2026-07-07 10:00" },
  { id: "run-v3.0", metrics: { roc_auc: 0.92 }, stage: "Archived", time: "2026-06-01 14:00" },
  { id: "run-v2.9", metrics: { roc_auc: 0.91 }, stage: "Archived", time: "2026-05-15 09:30" },
]

export default function ModelRegistryPage() {
  const [promoteOpen, setPromoteOpen] = useState(false)
  const [selectedRun, setSelectedRun] = useState<string | null>(null)

  const handlePromote = () => {
    // API call to promote would go here
    setPromoteOpen(false)
  }

  return (
    <div className="space-y-6">
      <h2 className="font-display text-xl font-medium text-mist">Model Registry</h2>

      <OpaquePanel className="p-6 h-[300px]">
        <h3 className="font-sans text-sm text-mist mb-4">ROC-AUC Trend</h3>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={[...runs].reverse()}>
            <XAxis dataKey="id" stroke="var(--mist)" opacity={0.5} fontSize={10} axisLine={false} tickLine={false} />
            <YAxis domain={[0.85, 1.0]} stroke="var(--mist)" opacity={0.5} fontSize={10} axisLine={false} tickLine={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'var(--trench)', borderColor: 'rgba(175,221,229,0.1)' }}
              itemStyle={{ fontFamily: 'var(--font-mono)' }}
            />
            <Line type="monotone" dataKey="metrics.roc_auc" stroke="var(--signal)" strokeWidth={2} dot={{ fill: 'var(--abyss)', strokeWidth: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      </OpaquePanel>

      <div className="mt-8">
        <h3 className="font-display text-lg font-medium text-mist mb-4">Run History</h3>
        <DataTable 
          data={runs}
          columns={[
            { header: "Run ID", cell: (item) => <span className="font-mono text-sm">{item.id}</span> },
            { header: "Timestamp", cell: (item) => <span className="font-mono text-xs text-mist/60">{item.time}</span> },
            { header: "ROC-AUC", cell: (item) => <span className="font-mono text-sm text-signal">{item.metrics.roc_auc}</span> },
            { header: "Stage", cell: (item) => (
                <span className={`text-xs px-2 py-1 rounded-full ${item.stage === 'Production' ? 'bg-signal/20 text-signal' : 'bg-mist/10 text-mist/60'}`}>
                  {item.stage}
                </span>
              )
            },
            { header: "Action", cell: (item) => (
                item.stage !== 'Production' ? (
                  <Dialog open={promoteOpen && selectedRun === item.id} onOpenChange={(open) => {
                    setSelectedRun(item.id)
                    setPromoteOpen(open)
                  }}>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm" className="h-7 text-xs border-mist/20 text-mist hover:bg-mist/10">Promote</Button>
                    </DialogTrigger>
                    <DialogContent className="bg-trench border-mist/20">
                      <DialogHeader>
                        <DialogTitle className="text-mist font-display">Promote Model to Production?</DialogTitle>
                        <DialogDescription className="text-mist/70 font-sans">
                          Are you sure you want to promote <span className="font-mono text-mist">{item.id}</span> to Production? 
                          This will immediately affect live traffic routing.
                        </DialogDescription>
                      </DialogHeader>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setPromoteOpen(false)} className="border-mist/20 text-mist hover:bg-mist/10">Cancel</Button>
                        <Button onClick={handlePromote} className="bg-signal text-[var(--text-on-signal)] hover:bg-signal/80">Confirm Promotion</Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                ) : null
              )
            }
          ]}
        />
      </div>
    </div>
  )
}
