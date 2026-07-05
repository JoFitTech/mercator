# Mercator Constitution

<!--
Sync Impact Report
Version: 1.0.0
Ratified: 2026-07-05
Last Amended: 2026-07-05
Scope: Establishes brownfield modernization governance for transforming the
existing Mercator repository into a personal stock analysis, prediction, and
preference dashboard.
Template updates required:
- .specify/templates/plan-template.md: Constitution Check must include the
  Mercator brownfield modernization gates.
-->

## Core Principles

### I. Brownfield Modernization Only

Mercator MUST be modernized in place inside the existing repository. New
features MUST preserve the currently working application until replacement
modules are implemented, tested, and wired into the same runtime path.

No separate greenfield application, duplicate repository, or parallel product
stack may be created for the replacement dashboard. Temporary compatibility
adapters are allowed only when they protect the current app while replacement
modules are introduced incrementally.

### II. Stock Analysis Scope, No Trade Execution

Mercator's target domain is personal stock analysis, prediction, ranking, and
preference scoring. The system MAY generate predictions, rankings, model-based
forecasts, and preference scores for securities.

The system MUST NOT execute trades, place orders, connect to a broker, automate
portfolio transactions, or present generated output as a final trading decision.
Final trading decisions remain outside Mercator and outside the system boundary.

### III. Data Architecture Is Preserved

MongoDB remains the raw API response store. MySQL remains the clean relational
analysis store. Implementations MUST preserve this separation unless a future
constitution amendment explicitly changes the architecture.

Raw external API payloads, provider metadata, ingestion status, and fetch
timestamps belong in MongoDB. Normalized securities, clean analysis entities,
scores, predictions, preferences, and relational query models belong in MySQL.
Cross-store synchronization MUST make missing, stale, incomplete, and failed
data states explicit and testable.

### IV. Rename Safely, Never Blindly

Insider-trade-specific Mercator concepts MUST be renamed to broader
stock-analysis concepts during implementation, based on prior repository
analysis and an explicit rename map. Blind global search-and-replace is
prohibited.

Rename batches MUST update imports, tests, UI references, documentation,
configuration, and database references together. A module rename is not complete
until the old and new runtime paths are understood, affected tests are updated,
and compatibility or migration behavior is documented where needed.

### V. Transparent Predictions And Data Quality

Every prediction, ranking, preference score, and model-based forecast MUST show
uncertainty, confidence, model quality, and data freshness to the user. These
signals must be tied to the data and model version used to produce the output.

Missing, stale, incomplete, low-quality, or failed data MUST be visible in the
Streamlit UI as text, not only by color, icon, chart styling, or layout. The UI
must help the user distinguish unavailable data from negative signals and from
valid low-confidence model output.

## Technology And Security Constraints

Streamlit remains the first user interface. Modernization MAY improve internal
services, models, repositories, tests, and UI pages, but initial user-facing
delivery must continue through the existing Streamlit application unless this
constitution is amended.

API keys, tokens, credentials, and secrets MUST remain in environment variables
or secret-management mechanisms already supported by the repository. Secrets
MUST NOT be hardcoded in code, tests, specs, logs, screenshots, seed data, or
documentation examples.

External data providers must be treated as unreliable. Provider failures, rate
limits, partial responses, stale timestamps, schema drift, and normalization
failures must be represented in data structures and surfaced in user-facing
status text where they affect analysis.

## Development Workflow And Quality Gates

Every feature plan MUST begin with repository analysis of the relevant current
modules before proposing replacements. Plans MUST identify the existing paths
that will be preserved, wrapped, renamed, replaced, or removed.

Implementation MUST proceed in small, verifiable increments. A change that
renames or replaces a domain module MUST include corresponding tests and must
avoid breaking the current working application before the replacement path is
available.

Tests MUST cover repository synchronization, data-quality state propagation,
prediction transparency fields, and UI-visible text for missing, stale,
incomplete, or failed data whenever a feature touches those behaviors.

Documentation and specs MUST make the no-broker/no-trade-execution boundary
explicit for prediction, ranking, preference, portfolio, or recommendation
features.

## Governance

This constitution supersedes conflicting implementation preferences, feature
plans, task lists, and ad hoc modernization shortcuts. When a feature conflicts
with these principles, the feature must be redesigned or the constitution must
be amended first.

Amendments require a documented rationale, a migration impact note for existing
code and data, and an update to affected Spec Kit templates. Versioning follows
semantic versioning: MAJOR for principle removals or incompatible governance
changes, MINOR for new principles or materially expanded requirements, and PATCH
for clarifications that do not change obligations.

All implementation plans and reviews MUST include a constitution check covering
brownfield preservation, data-store separation, rename safety, prediction
transparency, visible data-quality text, no trade execution, Streamlit-first UI,
and secret handling.

**Version**: 1.0.0 | **Ratified**: 2026-07-05 | **Last Amended**: 2026-07-05
