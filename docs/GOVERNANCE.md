# Repository Governance

This document defines the governance structure for the Kubeflow Pipelines Components Repository.

## Table of Contents

- [Two-Tier System](#two-tier-system)
- [Ownership Models](#ownership-models)
- [Tier Transitions](#tier-transitions)
- [Removal Policies](#removal-policies)
- [Deprecation Policy](#deprecation-policy)
- [Repository Roles](#repository-roles)
- [Decision Making](#decision-making)
- [Conflict Resolution](#conflict-resolution)
- [Policy Updates](#policy-updates)
- [Related Documentation](#related-documentation)
- [Background](#background)

## Repository Roles

*Key roles and responsibilities for governing and maintaining the repository.*

### KFP Component Repository Maintainer

Repository Maintainers are responsible for the stewardship of the Kubeflow Pipelines Components repository. They are defined by having thier GitHub username listed in the `approvers` section of the `OWNERS` file in the repository root.

Respository Maintiners key responsbilities include:
- Orchestrating releases
- Setting roadmaps and accepting KEPs related to Kubeflow Pipelines Components
- Managing the overall project, issues, etc
- General repository maintenance


### Core Component Maintainer

Core Component Owners are individuals responsible for maintaining an individual core-tier component or pipeline.  They are defined by having thier GitHub username listed in the `approvers` section of the `OWNERS` file of at least one individual core-tier component or pipeline.

Core Component Maintainer key responsibilities include:
- Acting as the main point of contact for their component(s).
- Reviewing and approving changes to their component(s).
- Ensuring ongoing quality and documentation for their component(s).
- Updating or transferring ownership when maintainers change.

Note that all components must have at least two listed owners for redundancy and review coverage.


### Third-Party Component Maintainers

Similar to a Core Component Maintainer, a Third-Party Maintainer is responsible for at least one Third-Party tier component or pipelines that they or their teams own.  They are defined by having thier GitHub username listed in the `approvers` section of the `OWNERS` file of at least one individual third-party tier component or pipeline.

Third-Party Component Maintainer key responsibilities include:
- Acting as the main point of contact for their component(s).
- Reviewing and approving changes to their component(s).
- Ensuring ongoing quality and documentation for their component(s).
- Updating or transferring ownership when maintainers change.

Note that all components must have at least two listed owners for redundancy and review coverage.

## Two-Tier System

*The repository uses a two-tier classification system distinguishing officially supported components from community contributions.*

## Core Tier


**Officially supported components** maintained by at least 2 Component Core Maintainers.

**Requirements:**
- Security review passed
- Complete documentation
- Active maintenance commitment
- Backward compatibility guarantees
- Unit test provided with exceptional code coverage

**Benefits:**
- Official support and maintenance
- Included in python package releases
- Priority for bug fixes
- Long-term stability guarantees

### Third-Party Tier

**Community-contributed components** with lighter requirements.

**Requirements:**
- Unit test provided
- Basic documentation (README, examples)
- At least 2 maintainers

**Benefits:**
- Community visibility
- Shared maintenance burden
- Faster contribution process than Core components
- Good for idea incubation
- Potential for promotion to Core tier

## Ownership Models

*How ownership, maintenance, and decision-making responsibilities are distributed across tiers.*

### Core Tier
- **Owned by**: Kubeflow community
- **Maintained by**: Designated maintainer teams
- **Decisions by**: Repository and Core Component Maintainers consensus
- **Support**: Official community support

### Third-Party Tier (no Kubeflow org membership required)
- **Owned by**: Original contributors
- **Maintained by**: Component owners
- **Decisions by**: Component owners
- **Support**: Best-effort community support

## Tier Transitions

*Process for moving components between Core and Third-Party tiers.*

## Removal Policies

*Timeline and criteria for removing inactive or problematic components from the repository.*

### Verification Process (9 months)
Components are marked for verification if:
- No updates in over 9 months
- Maintainers are unresponsive
- Compatibility issues

### Removal Process (12 months)
After 12 months of inactivity:
1. **Notice**: 30-day removal notice
2. **Community input**: 2-week feedback period
3. **Final decision**: KFP Component Repository Maintainers
4. **Removal**: Delete component code from repository

### Emergency Removal
Immediate removal for:
- Severe and/or compatibility-breaking issues
- Critical security vulnerabilities
- Legal issues
- Malicious code

## Deprecation Policy

*Structured approach to deprecating core components with adequate notice and migration support.*

### Two-Release Policy
Components will be deprecated for a minimum of 2 Kubeflow releases before removal.

**Process:**
1. **Deprecation notice**: Mark as deprecated
2. **Migration guide**: Provide alternatives
3. **Community notice**: Announce in releases
4. **Removal**: After 2 releases


## Decision Making

*Framework for making technical, policy, and strategic decisions within the community.*

### Decision Types
- **Technical**: Component owners → KFP Component Repository Maintainers 
- **Policy**: KFP Component Repository Maintainers 
- **Strategic**: KFP Component Repository Maintainers 

### Process
1. **Proposal**: Create GitHub issue/RFC
2. **Discussion**: Community feedback
3. **Decision**: Appropriate authority level
4. **Implementation**: Assign and track

## Policy Updates

*How governance policies are updated to evolve with community needs and learnings.*

**Process:**
1. **RFC**: Propose changes via GitHub issue
2. **Community review**: 2-week feedback period
3. **Maintainers approval**: Majority vote required
4. **Implementation**: Update documentation and processes

**Criteria for updates:**
- Community needs evolution
- Process improvements
- Conflict resolution learnings
- External requirements changes

---

This governance model ensures quality, sustainability, and community collaboration while maintaining clear processes and expectations.

## Related Documentation

- **[Contributing Guide](CONTRIBUTING.md)** - Complete contributor guide with setup, testing, and workflow
- **[Best Practices Guide](BESTPRACTICES.md)** - Component development best practices *(coming soon)*
- **[Agents Guide](AGENTS.md)** - AI agent guidance *(coming soon)*

## Background

This governance model is based on [KEP-913: Components Repository](https://github.com/kubeflow/community/tree/master/proposals/913-components-repo), which established the framework for a curated collection of reusable Kubeflow Pipelines components with clear quality standards and community governance.

For questions about governance, contact the pipelines-components repository maintainers (as noted by `approvers` in top-level `OWNERS` file) or open a GitHub issue.
