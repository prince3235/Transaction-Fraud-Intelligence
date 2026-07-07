"use client"

import { OpaquePanel } from "@/components/shared/OpaquePanel"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"

interface ShapWaterfallProps {
  features?: Record<string, number>
}

export function ShapWaterfall({ features }: ShapWaterfallProps) {
  if (!features || Object.keys(features).length === 0) {
    return <div className="text-mist/40 text-sm">No feature contributions available.</div>
  }

  const data = Object.entries(features)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 10); // top 10 features

  return (
    <OpaquePanel className="p-4 h-[300px]">
      <h3 className="text-sm font-sans text-mist mb-4">Feature Contributions (SHAP)</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, left: 40, bottom: 0 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" stroke="var(--mist)" opacity={0.5} fontSize={10} axisLine={false} tickLine={false} />
          <Tooltip 
            cursor={{ fill: 'var(--mist)', opacity: 0.05 }}
            contentStyle={{ backgroundColor: 'var(--trench)', borderColor: 'rgba(175,221,229,0.1)' }}
            itemStyle={{ fontFamily: 'var(--font-mono)' }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.value > 0 ? 'var(--ember)' : 'var(--signal)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </OpaquePanel>
  )
}
