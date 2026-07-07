"use client"

import { useState } from "react"
import { GlassPanel } from "@/components/shared/GlassPanel"
import { OpaquePanel } from "@/components/shared/OpaquePanel"
import { Button } from "@/components/ui/button"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { PlayCircle } from "lucide-react"

const defaultJson = `{
  "transaction_id": "sim-001",
  "amount": 25000.00,
  "user_id": "u-492",
  "ip_address": "192.168.1.1",
  "device_id": "dev-99",
  "timestamp": "2026-07-07T12:00:00Z"
}`

export default function SimulationPage() {
  const [inputJson, setInputJson] = useState(defaultJson)
  const [result, setResult] = useState<any>(null)
  const [isSimulating, setIsSimulating] = useState(false)

  const handleSimulate = async () => {
    setIsSimulating(true)
    try {
      // Validate JSON
      JSON.parse(inputJson)
      
      // Mock API delay
      await new Promise(r => setTimeout(r, 800))
      
      setResult({
        status: "success",
        ml_score: 0.89,
        ml_risk_level: "high",
        rules_triggered: ["Large Amount Offline"],
        final_action: "FLAG",
        execution_time_ms: 45
      })
    } catch (e) {
      setResult({
        status: "error",
        message: "Invalid JSON format."
      })
    }
    setIsSimulating(false)
  }

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-8rem)]">
      <h2 className="font-display text-xl font-medium text-mist flex-shrink-0">Simulation Sandbox</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        <GlassPanel className="p-0 flex flex-col overflow-hidden">
          <div className="p-4 border-b border-mist/10 flex justify-between items-center bg-foam-strong">
            <h3 className="font-display text-sm text-mist">Transaction Payload (JSON)</h3>
            <Button 
              onClick={handleSimulate} 
              disabled={isSimulating}
              size="sm"
              className="bg-signal text-[var(--text-on-signal)] hover:bg-signal/80 h-7 text-xs"
            >
              <PlayCircle className="w-3.5 h-3.5 mr-1.5" />
              Run Simulation
            </Button>
          </div>
          <textarea 
            value={inputJson}
            onChange={(e) => setInputJson(e.target.value)}
            className="flex-1 w-full bg-abyss p-4 text-sm font-mono text-mist/90 outline-none resize-none"
            spellCheck={false}
          />
        </GlassPanel>

        <OpaquePanel className="p-6 flex flex-col">
          <h3 className="font-display text-lg text-mist mb-6">Simulation Results</h3>
          
          {!result && (
            <div className="flex-1 flex items-center justify-center text-sm font-sans text-mist/40">
              Run a simulation to see ML scores and Rule Engine outcomes.
            </div>
          )}

          {result?.status === "error" && (
            <div className="text-ember bg-ember/10 p-4 rounded-md border border-ember/20 font-mono text-sm">
              {result.message}
            </div>
          )}

          {result?.status === "success" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-trench/50 border border-mist/10 p-4 rounded-lg">
                  <p className="text-xs text-mist/60 uppercase mb-1">ML Fraud Score</p>
                  <p className="font-mono text-2xl text-ember">{(result.ml_score * 100).toFixed(1)}%</p>
                  <RiskBadge level={result.ml_risk_level} className="mt-2" />
                </div>
                <div className="bg-trench/50 border border-mist/10 p-4 rounded-lg">
                  <p className="text-xs text-mist/60 uppercase mb-1">Final Action</p>
                  <p className="font-display text-2xl text-signal">{result.final_action}</p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-sans text-mist/80 mb-2 border-b border-mist/10 pb-1">Rules Triggered</h4>
                {result.rules_triggered.length > 0 ? (
                  <ul className="space-y-2">
                    {result.rules_triggered.map((r: string, i: number) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-mist/90">
                        <span className="w-1.5 h-1.5 rounded-full bg-signal" /> {r}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-mist/40">No rules triggered.</p>
                )}
              </div>

              <div className="mt-auto pt-6 border-t border-mist/10">
                <p className="font-mono text-xs text-mist/30">Execution Time: {result.execution_time_ms}ms</p>
              </div>
            </div>
          )}
        </OpaquePanel>
      </div>
    </div>
  )
}
