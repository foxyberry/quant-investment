/**
 * Condition Registry - Type definitions only.
 *
 * Condition data is now fetched from the backend API via useConditions() context.
 * This file retains type exports for backwards compatibility.
 */

export interface ConditionParam {
  name: string;
  type: 'int' | 'float' | 'str' | 'bool';
  default: unknown;
  description: string;
}

export interface ConditionMeta {
  key: string;
  label: string;
  description: string;
  category: string;
  params: ConditionParam[];
  recommended: boolean;
  order: number;
}
