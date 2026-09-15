# OpenMedia Constitution

## Core Principles

### I. Social Media Downloading

OpenMedia's purpose is to download video, audio, and images from social media sources,
including YouTube, LinkedIn, and Instagram. Features MUST serve this purpose or the
operation of the downloader. Each feature specification MUST identify the platforms,
media types, and user journeys it supports; naming a platform does not imply support
for every content type or access mode. This keeps delivery incremental and support
claims verifiable.

### II. Telegram Bot Interface

Telegram Bot MUST be the user interface for the application. Download workflows MUST
allow users to submit source links and receive either the requested media or a clear
explanation of why delivery failed. Specifications MUST define user-visible behavior
for invalid links, unsupported content, download failures, and delivery limits.
Download logic MUST remain separate from Telegram message handling so that it can be
tested and maintained independently.

### III. Python by Default

The backend MUST use Python by default to keep development and operation simple.
Supporting tools in other languages MAY be used when needed by a chosen downloader or
media processor. A proposal to replace Python as the backend MUST document the concrete
need and tradeoffs in the implementation plan. Architecture MUST begin with the simplest
arrangement that meets the feature requirements; additional services MUST have a
requirement-based justification.

### IV. Reuse Open Source Solutions

Implementation planning MUST evaluate existing open source downloaders and media tools
before proposing custom extraction or processing code. When an existing solution meets
the requirements, it SHOULD be reused to reduce maintenance of platform-specific logic;
a custom implementation MUST explain the unmet requirement or maintenance tradeoff.
Selected dependencies MUST have their purpose, license compatibility, and version
constraints recorded. Platform-specific integrations MUST be isolated so that upstream
changes can be addressed without rewriting the bot workflow.

### V. Container Deployment

The application MUST support deployment as a container. The container build MUST include
its required runtime dependencies, and deployment instructions MUST document startup,
configuration, and any storage requirements. Credentials and environment-specific
settings MUST be supplied at runtime rather than embedded in source code or the image.
Container deployment MUST be verified before a release is considered deployable.

## Product and Technical Constraints

- Feature specifications MUST state supported source access modes, output formats, and
  delivery behavior. Private content, authentication, playlists, and bulk downloads
  require explicit feature scope before implementation.
- Plans MUST account for the applicable Telegram and downloader limits and define what
  users see when a request exceeds them. Changing external limits MUST NOT be assumed
  to be permanent project constants.
- Download execution MUST have defined timeout, concurrency, and temporary storage limits.
  Temporary media MUST have a documented cleanup policy covering success and failure.
- Bot tokens and any source credentials MUST be excluded from logs and version control.
  User-facing errors MUST explain the outcome without exposing internal credentials.
- Databases, queues, and additional services MUST be introduced only when a documented
  requirement calls for them.

## Development Workflow and Quality Gates

- Feature work MUST begin with a specification describing user outcomes and acceptance
  criteria, followed by an implementation plan and an ordered task list.
- Plans MUST identify reused components, supported platform and media combinations,
  deployment needs, and any justified exceptions to these principles.
- Validation MUST cover the changed behavior, including a successful download and
  delivery path and relevant failure paths when those workflows change.
- Automated checks MUST use controlled fixtures or substitutes where practical so that
  routine validation does not depend on live social media availability. Live integration
  checks MUST be identified separately, with their results and limitations recorded.
- Changes to the container or runtime setup MUST include a build and startup check.
- Completion reports MUST identify the checks performed, results, and remaining support
  limitations. Review MUST confirm that implementation matches the feature acceptance
  criteria and this constitution.

## Governance

This constitution governs OpenMedia specifications, plans, tasks, and implementation.
Conflicting project documents MUST be brought into alignment before affected work is
considered complete. Exceptions MUST be recorded in the relevant plan with their reason,
impact, and validation; changing a governing principle requires an amendment.

Amendments MUST document the proposed change and rationale, assess affected feature
artifacts, and receive project maintainer approval before adoption. The constitution
version and last-amended date MUST be updated for every substantive amendment, while the
original ratification date remains unchanged.

Versioning follows semantic versioning: MAJOR for incompatible principle removals or
redefinitions, MINOR for new principles or materially expanded guidance, and PATCH for
clarifications that do not change obligations. Reviews MUST check constitution compliance
and identify any affected documents requiring follow-up.

**Version**: 1.0.0 | **Ratified**: 2026-09-15 | **Last Amended**: 2026-09-15
