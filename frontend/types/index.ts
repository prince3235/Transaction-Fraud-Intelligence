export type RiskLevel = 'high' | 'medium' | 'low';

export interface PredictionLog {
  id: string;
  transaction_id: string;
  amount: number;
  risk_level: RiskLevel;
  status: 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED';
  timestamp: string;
  fraud_probability: number;
  features?: Record<string, number>;
}

export interface FraudCase {
  id: string;
  prediction_log_id: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED';
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  assigned_to?: string;
  created_at: string;
  updated_at: string;
  notes?: string;
  prediction?: PredictionLog;
}

export interface AuditLogEntry {
  id: string;
  user_id: string;
  action: string;
  resource_id?: string;
  details?: string;
  timestamp: string;
}

export interface BusinessRule {
  id: string;
  name: string;
  condition_json: string;
  action: 'FLAG' | 'BLOCK' | 'ALLOW';
  active: boolean;
  created_at: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'Junior Analyst' | 'Senior Analyst' | 'Data Scientist' | 'Admin/Executive';
  avatar_url?: string;
}
