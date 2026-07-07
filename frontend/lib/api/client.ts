import { z } from 'zod';
import { PredictionLog, FraudCase, AuditLogEntry, BusinessRule } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Schemas for validation
export const PredictionLogSchema = z.object({
  id: z.string(),
  transaction_id: z.string(),
  amount: z.number(),
  risk_level: z.enum(['high', 'medium', 'low']),
  status: z.enum(['PENDING_REVIEW', 'APPROVED', 'REJECTED']),
  timestamp: z.string(),
  fraud_probability: z.number(),
  features: z.record(z.string(), z.number()).optional()
});

export const PaginatedAlertsSchema = z.object({
  items: z.array(PredictionLogSchema),
  total: z.number(),
  page: z.number(),
  pages: z.number()
});

export const CaseDetailSchema = z.object({
  id: z.string(),
  prediction_log_id: z.string(),
  status: z.enum(['OPEN', 'IN_PROGRESS', 'RESOLVED']),
  priority: z.enum(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
  assigned_to: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  notes: z.string().optional(),
  prediction: PredictionLogSchema.optional()
});

// API Functions
export const api = {
  async getAlerts(page = 1, status?: string): Promise<PredictionLog[]> {
    // We expect the backend to return { items: [] } or just an array.
    // For this mock implementation we assume it returns an array of alerts.
    const res = await fetch(`${API_BASE}/alerts?page=${page}${status ? `&status=${status}` : ''}`);
    if (!res.ok) throw new Error("Failed to fetch alerts");
    const data = await res.json();
    return z.array(PredictionLogSchema).parse(data);
  },

  async getCase(caseId: string) {
    const res = await fetch(`${API_BASE}/cases/${caseId}`);
    if (!res.ok) throw new Error("Failed to fetch case");
    const data = await res.json();
    return CaseDetailSchema.parse(data);
  }
};
