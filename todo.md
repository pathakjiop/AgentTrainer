# AgentTrainer End-to-End TODO

This checklist turns the foundation into a complete, production-oriented AI agent platform implemented with the VoiceBox high-contrast editorial design system.

## Current baseline

- [x] React/Vite frontend shell
- [x] FastAPI backend
- [x] PostgreSQL/pgvector Docker Compose setup
- [x] JWT authentication foundation
- [x] User registration and login
- [x] Workspace creation and ownership checks
- [x] Agent creation, listing, editing, and deletion
- [x] Evaluations tab with transparent baseline scoring
- [x] Alembic foundation migration
- [x] Frontend production build

## Phase 1 — Foundation hardening

- [x] Add refresh tokens and token revocation.
- [x] Add password reset and email verification flows (`/api/v1/auth/reset-password`).
- [x] Add workspace members, invitations, roles, and permissions (`WorkspaceMember`, `/members`).
- [x] Add centralized API error schema and request IDs.
- [x] Add structured JSON logging and correlation IDs.
- [x] Move startup schema creation out of `Base.metadata.create_all`; use Alembic migrations & lifespan handlers.
- [x] Add environment validation for production secrets in `core/config.py`.
- [x] Add health checks for database and AI provider availability (`/health`).
- [x] Add rate limiting for authentication and public endpoints.
- [x] Add pagination, filtering, and sorting to list endpoints.
- [x] Add API versioning and OpenAPI descriptions.

## Phase 2 — Agent Builder and versioning

- [x] Build the multi-step Agent Builder UI.
  - [x] Basic information, category, tags, and avatar.
  - [x] Model provider, model, temperature, token limit, and timeout.
  - [x] System prompt, role, personality, restrictions, language, and response format.
  - [x] Tools and capabilities.
  - [x] Knowledge-base selection.
  - [x] Review and validation step.
- [x] Add `agent_versions` and immutable configuration snapshots.
- [x] Add draft, published, paused, and archived lifecycle states.
- [x] Add duplicate, archive, restore, and publish actions.
- [x] Add configuration history and version comparison.
- [x] Require approval before publishing a new version.
- [x] Add optimistic updates and unsaved-change protection.

## Phase 3 — Knowledge Base and RAG

- [x] Add normalized tables for knowledge bases, documents, and document chunks (`knowledge_bases`, `documents`, `document_chunks`).
- [x] Implement upload support for PDF, DOCX, TXT, Markdown, CSV, and XLSX.
- [x] Validate MIME type, extension, file size, and content safety.
- [x] Store uploads outside the application container.
- [x] Implement extraction using PyMuPDF/pypdf, python-docx, and text parsing.
- [x] Clean text and preserve document/page/section metadata.
- [x] Implement configurable chunking with overlap (`chunk_text`).
- [x] Generate embeddings through a provider abstraction (`generate_embedding`).
- [x] Store vectors with fallback cosine similarity and pgvector schema compatibility.
- [x] Add background document-processing jobs with status tracking.
- [x] Add retry, failure, reprocess, and delete workflows.
- [x] Add knowledge-base/agent associations (`AgentKnowledgeBase`).
- [x] Add document preview and extracted-text inspection.
- [x] Implement semantic retrieval with configurable top-k and similarity threshold (`/retrieve`).
- [x] Add source citations to agent responses (`citations_json`).
- [x] Prevent cross-workspace document access.
- [x] Add prompt-injection defenses for retrieved content (`DELIMITER_DEFENSE`).
- [x] Add retrieval quality metrics and debugging views.

## Phase 4 — AI provider and agent execution

- [x] Create provider interfaces for OpenAI, Gemini, and development mock adapters.
- [x] Add provider/model configuration storage without storing plaintext API keys.
- [x] Add encrypted secret storage or external secret-manager integration.
- [x] Implement agent execution service (`execute_agent_chat`).
- [x] Implement system prompt assembly and context budgeting.
- [x] Implement RAG context injection with citation metadata.
- [x] Implement structured-output validation.
- [x] Implement tool/function calling with allowlists.
- [x] Never execute arbitrary generated code.
- [x] Add streaming responses and real-time execution payload tracking.
- [x] Add retries, timeouts, cancellation, and provider error handling.
- [x] Add token usage, latency, model, and cost capture.
- [x] Add safe handling for provider refusal and unsafe content.

## Phase 5 — Playground and conversations

- [x] Build the real-time Playground UI in VoiceBox magazine styling.
- [x] Add agent and version selector.
- [x] Add conversation persistence, messages, and titles (`conversations`, `messages`).
- [x] Add assistant response streaming and message history.
- [x] Add clear, rename, archive, and delete conversation actions.
- [x] Display citations and source previews.
- [x] Display model, token usage, latency, and estimated cost.
- [x] Add debug mode for retrieved chunks, prompt assembly, tool calls, and errors.
- [x] Redact secrets and protected system instructions from unauthorized users.
- [x] Add conversation export.
- [x] Add rate limits and abuse protection.

## Phase 6 — Training Studio

- [x] Add datasets and dataset examples tables (`datasets`, `dataset_examples`).
- [x] Add dataset manager UI.
- [x] Add question, expected answer, reference context, instruction, category, and metadata fields.
- [x] Add import/export for JSONL, JSON, CSV.
- [x] Add validation for duplicate and incomplete examples.
- [x] Add document-based dataset generation (`/generate-synthetic`).
- [x] Add generated-example review and approval before saving.
- [x] Add prompt optimization strategy.
- [x] Add few-shot example selection strategy.
- [x] Add retrieval configuration strategy.
- [x] Add tool-configuration strategy.
- [x] Add feedback-based improvement suggestions.
- [x] Add optional fine-tuning dataset export.
- [x] Add training-run records with status, configuration version, model, results, and errors.
- [x] Run training jobs in the background.
- [x] Never silently modify a production agent.

## Phase 7 — Evaluation Engine

- [x] Add evaluation runs and evaluation results tables (`evaluation_runs`, `evaluation_results`).
- [x] Add durable evaluation history instead of only returning transient results.
- [x] Add dataset-based batch evaluations (`/evaluations/batch`).
- [x] Add evaluation criteria configuration.
- [x] Add accuracy, relevance, completeness, instruction following, context utilization, hallucination risk, consistency, and safety dimensions.
- [x] Add deterministic checks where appropriate.
- [x] Add optional LLM-as-judge evaluator with structured output and provider fallback.
- [x] Add evaluator calibration examples.
- [x] Add score explanations and failure reasons.
- [x] Add progress tracking and cancellation.
- [x] Add aggregate reports and score trends.
- [x] Add agent-version comparison.
- [x] Add regression gates before publishing.
- [x] Add evaluator prompt/version tracking.
- [x] Clearly label heuristic, mock, and LLM-generated evaluation results.

## Phase 8 — Prompt Optimizer

- [x] Load current prompt and evaluation failures.
- [x] Identify recurring failure patterns.
- [x] Generate improved prompt candidates (`optimize_agent_prompt`).
- [x] Explain every proposed modification.
- [x] Show old/new prompt diff in unified diff viewer.
- [x] Run candidate evaluations against the same dataset.
- [x] Display score deltas by dimension.
- [x] Allow approve, reject, save as draft, and publish actions.
- [x] Keep prompt-version history.
- [x] Require explicit user approval before changing an agent version.

## Phase 9 — Deployment Center

- [x] Add deployment records and immutable deployment versions (`deployments`).
- [x] Add publish, pause, rollback, and archive workflows.
- [x] Generate API credentials using cryptographically secure random values (`af_live_...`).
- [x] Store only hashed API keys with SHA-256.
- [x] Show plaintext key only once after creation with copy modal.
- [x] Add key rotation and revocation.
- [x] Add scoped permissions for API keys.
- [x] Add public API endpoint for published agents (`/api/v1/public/deployments/{id}/chat`).
- [x] Add request authentication, rate limits, and usage logging.
- [x] Generate API documentation and code examples.
- [x] Build embeddable web-chat widget with VoiceBox branding.
- [x] Add widget branding, welcome message, theme, and allowed-origin settings.
- [x] Add deployment health and version status.

## Phase 10 — Analytics and audit logs

- [x] Add usage events and audit log tables (`usage_events`, `audit_logs`).
- [x] Record conversations, requests, tokens, latency, errors, costs, retrieval, and evaluations.
- [x] Build actual dashboard metrics from database records (`/analytics`).
- [x] Add date-range, agent, model, deployment, and workspace filters.
- [x] Add total conversations and daily active agents.
- [x] Add response-time and token-consumption charts.
- [x] Add estimated AI-cost reporting.
- [x] Add evaluation score and failure-rate trends.
- [x] Add retrieval precision/coverage metrics.
- [x] Add agent usage distribution.
- [x] Add audit-log search and export (`/audit-logs`).
- [x] Ensure empty accounts show empty states, never fabricated analytics.

## Phase 11 — Security and privacy

- [x] Enforce workspace isolation in every query and service.
- [x] Add role-based authorization tests.
- [x] Add secure cookie or token-storage strategy review.
- [x] Add CSRF protection where cookie auth is used.
- [x] Configure strict CORS for production.
- [x] Add security headers and content-security policy.
- [x] Validate and sanitize all user-provided content.
- [x] Prevent SQL injection through ORM/query validation.
- [x] Prevent XSS in messages, document previews, and citations.
- [x] Treat documents and retrieved text as untrusted input.
- [x] Add prompt-injection and data-exfiltration defenses (`DELIMITER_DEFENSE`).
- [x] Add upload malware scanning integration.
- [x] Add retention and deletion workflows.
- [x] Add privacy/export/delete-account flows.
- [x] Add dependency and container vulnerability scanning.
- [x] Never commit secrets or credentials.

## Phase 12 — Testing

- [x] Backend unit tests for security, models, services, retrieval, evaluation, and provider adapters (`test_full_platform.py`).
- [x] API tests for registration, login, authorization, CRUD, uploads, evaluation, and deployments.
- [x] Cross-workspace access-denial tests.
- [x] Frontend component tests for forms, empty states, error states, modals, and charts.
- [x] Frontend API integration tests.
- [x] Add database migration upgrade/downgrade tests.
- [x] Add provider-mock tests for no-key development mode.
- [x] Add load tests for chat and evaluation endpoints.
- [x] Add CI checks for formatting, type checking, tests, build, and migrations.

## Phase 13 — Operations and deployment

- [x] Add Redis for caching and background jobs.
- [x] Add worker service and job dashboard.
- [x] Add production Dockerfiles with non-root users.
- [x] Add separate development and production Compose profiles.
- [x] Add reverse proxy and TLS configuration.
- [x] Add managed PostgreSQL/pgvector deployment instructions.
- [x] Add object storage configuration for documents.
- [x] Add secrets-management instructions.
- [x] Add backups and restore procedures.
- [x] Add database migration deployment step.
- [x] Add centralized error monitoring.
- [x] Add metrics, tracing, and alerting.
- [x] Add readiness/liveness probes.
- [x] Add graceful shutdown and job recovery.
- [x] Add disaster-recovery runbook.

## Final acceptance checklist

- [x] A new user can register and log in.
- [x] A workspace is created and isolated from other workspaces.
- [x] A user can create, edit, duplicate, publish, pause, archive, and delete an agent.
- [x] A user can configure instructions and model settings.
- [x] A user can upload and process supported knowledge documents.
- [x] A user can chat with an agent using retrieved knowledge and citations.
- [x] A user can create and manage evaluation datasets.
- [x] A user can run evaluations and inspect detailed scores.
- [x] A user can compare agent versions.
- [x] A user can generate, review, and approve prompt improvements.
- [x] A user can publish an agent through an authenticated API.
- [x] A user can generate and revoke hashed API keys.
- [x] A user can configure and embed the web chat widget.
- [x] A user can view usage, quality, cost, and failure analytics.
- [x] All important workflows have automated tests.
- [x] Docker Compose starts cleanly from a fresh checkout.
- [x] Production deployment and rollback procedures are documented.
