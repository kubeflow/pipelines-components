# Repository Governance

This document defines the governance structure for the Kubeflow Pipelines components repository.

## Table of Contents

- [Repository Roles](#repository-roles)
- [Ownership Model](#ownership-model)
- [Verification and Removal](#verification-and-removal)
- [Deprecation Policy](#deprecation-policy)
- [Decision Making](#decision-making)
- [Policy Updates](#policy-updates)
- [Related Documentation](#related-documentation)
- [Background](#background)

## Repository Roles

*Key roles and responsibilities for governing and maintaining the repository.*

### KFP Components Repository Maintainer

Repository Maintainers steward the Kubeflow Pipelines Components repository. They are listed in
the root `OWNERS` file under `approvers`.

Responsibilities:

- Orchestrate releases
- Set roadmaps and accept KEPs related to Kubeflow Pipelines Components
- Manage overall project health and issue triage
- Maintain policy and automation

### Component or Pipeline Owner

Owners are listed as `approvers` in an asset's `OWNERS` file. Every asset must have at least one
owner to ensure accountability and continuity. Approvers must be Kubeflow community members.

Responsibilities:

- Act as the main point of contact for their asset(s)
- Review and approve changes to their asset(s)
- Keep metadata, documentation, and verification fresh
- Update or transfer ownership when maintainers change

## Ownership Model

- **Owned by**: Kubeflow community
- **Maintained by**: Asset owners listed in each `OWNERS` file
- **Support**: Officially part of the single catalog; support expectations come from the
  verification SLA and CI requirements

## Verification and Removal

- Assets must keep `lastVerified` fresh (within 12 months) and pass CI.
- At ~9 months without verification, automation/open issues should prompt owners to refresh
  metadata and validation.
- At 12 months without verification or for unresolved compatibility/security issues, Repository
  Maintainers may remove the asset from the catalog.
- Emergency removal may occur for critical security, legal, or malicious code issues.

## Deprecation Policy

- Use a two-release deprecation window when feasible.
- Steps:
  1. Mark deprecated in metadata/README and communicate in release notes.
  2. Provide migration guidance or alternatives.
  3. Remove after two Kubeflow releases (or sooner for emergencies as noted above).

## Decision Making

*Framework for making technical, policy, and strategic decisions within the community.*

### Decision Types

- **Technical (asset-level)**: Asset owners, with escalation to Repository Maintainers if needed
- **Policy**: Repository Maintainers
- **Strategic**: Repository Maintainers

### Process

1. **Proposal**: Create a GitHub issue or RFC
2. **Discussion**: Community feedback
3. **Decision**: Appropriate authority level
4. **Implementation**: Track to completion

## Policy Updates

**Process:**

1. **RFC/Issue**: Propose changes via GitHub issue
2. **Community review**: 2-week feedback period where practical
3. **Maintainer approval**: Majority of Repository Maintainers
4. **Implementation**: Update documentation and automation

**Criteria for updates:**

- Community needs and process improvements
- Conflict resolution learnings
- External requirements and security posture

---

This governance model ensures quality, sustainability, and community collaboration while keeping
a single, consistent catalog.

## Related Documentation

- **[Contributing Guide](CONTRIBUTING.md)** - Contributor setup, testing, and workflow
- **[Best Practices Guide](BESTPRACTICES.md)** - Component/pipeline authoring guidance
- **[Agents Guide](AGENTS.md)** - AI agent guidance

## Background

Based on
[KEP-913: Components Repository](https://github.com/kubeflow/community/tree/master/proposals/913-components-repo),
establishing a curated catalog of reusable Kubeflow Pipelines assets with clear quality standards
and community governance.

For questions about governance, contact the Repository Maintainers (root `OWNERS`) or open a GitHub issue.
