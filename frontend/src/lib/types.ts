export interface Proposal {
  id: string;
  original_path: string;
  original_name: string;
  proposed_name: string;
  proposed_folder: string;
  confidence: number;
  matched_rule: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'corrected';
}

export interface RuleProfile {
  id: string;
  name: string;
  description: string;
  rules: Rule[];
}

export interface Rule {
  id: string;
  profile_id: string;
  patterns: string[];
  target_name_template: string;
  target_folder_template: string;
  priority: number;
  examples: string[];
}

export interface AuditEntry {
  id: number;
  timestamp: string;
  action: string;
  source: string;
  target: string | null;
  rule_id: string | null;
  details: Record<string, any>;
}

export interface AppConfig {
  [key: string]: unknown;
}
