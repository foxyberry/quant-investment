/**
 * OpenAPI-generated type utilities.
 *
 * Run `npm run gen:api` (backend running) or `npm run gen:api:file` (from openapi.json)
 * to regenerate `schema.d.ts` from the FastAPI OpenAPI spec.
 *
 * Usage:
 *   import type { components, paths } from '@/lib/api/schema'
 *   type Strategy = components['schemas']['StrategyRead']
 *   type RunResponse = paths['/api/strategy/run']['post']['responses']['200']['content']['application/json']
 *
 * The schema.d.ts file is gitignored (generated artifact).
 * Check in a snapshot when the API contract stabilises.
 */

// Re-export convenience types once schema.d.ts is generated.
// Until then this file documents the codegen contract.
export type {};
