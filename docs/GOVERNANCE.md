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

## Two-Tier System

*Classification system distinguishing officially supported components from community contributions.*

### Core Tier

**Officially supported components** maintained by the Kubeflow community.

**Requirements:**
- 90% test coverage (unit, integration, e2e)
- Security review passed
- Complete documentation
- Active maintenance commitment
- Backward compatibility guarantees

**Benefits:**
- Official support and maintenance
- Included in releases
- Priority for bug fixes
- Long-term stability guarantees

### Third-Party Tier

**Community-contributed components** with lighter requirements.

**Requirements:**
- 80% test coverage
- Basic documentation (README, examples)
- At least 2 maintainers
- Working implementation

**Benefits:**
- Community visibility
- Shared maintenance burden
- Faster contribution process
- Innovation sandbox

## Ownership Models

*How ownership, maintenance, and decision-making responsibilities are distributed across tiers.*

### Core Tier
- **Owned by**: Kubeflow community
- **Maintained by**: Designated maintainer teams
- **Decisions by**: Steering committee consensus
- **Support**: Official community support

### Third-Party Tier
- **Owned by**: Original contributors
- **Maintained by**: Component owners
- **Decisions by**: Component owners
- **Support**: Best-effort community support

## Tier Transitions

*Process for moving components between Core and Third-Party tiers.*

### Promotion to Core
1. **Nomination**: Any maintainer can nominate
2. **Review**: Technical and governance review
3. **Requirements**: Must meet all core tier requirements
4. **Decision**: Steering committee approval
5. **Timeline**: 4-6 weeks review process

### Demotion from Core
Triggers:
- Maintenance neglect (>6 months)
- Security issues unaddressed
- Breaking changes without migration
- Community consensus

## Removal Policies

*Timeline and criteria for removing inactive or problematic components from the repository.*

### Verification Process (9 months)
Components are marked for verification if:
- No updates in 9 months
- Maintainers unresponsive
- Compatibility issues

### Removal Process (12 months)
After 12 months of inactivity:
1. **Notice**: 30-day removal notice
2. **Community input**: 2-week feedback period
3. **Final decision**: Steering committee
4. **Archive**: Move to archived repository

### Emergency Removal
Immediate removal for:
- Critical security vulnerabilities
- Legal issues
- Malicious code

## Deprecation Policy

*Structured approach to deprecating components with adequate notice and migration support.*

### Two-Release Policy
Components deprecated for 2 Kubeflow releases before removal.

**Process:**
1. **Deprecation notice**: Mark as deprecated
2. **Migration guide**: Provide alternatives
3. **Community notice**: Announce in releases
4. **Removal**: After 2 releases

## Repository Roles

*Key roles and responsibilities for governing and maintaining the repository.*

### Steering Committee
- **Role**: Strategic decisions and governance
- **Members**: 5-7 senior community members
- **Term**: 2 years, staggered

### Repository Maintainers
- **Role**: Day-to-day repository management
- **Responsibilities**: Reviews, releases, community support
- **Requirements**: Active contributor, community trust

### Component Owners
- **Role**: Individual component maintenance
- **Responsibilities**: Updates, bug fixes, user support
- **Requirements**: Technical expertise, time commitment

## Decision Making

*Framework for making technical, policy, and strategic decisions within the community.*

### Decision Types
- **Technical**: Component owners → maintainers → steering committee
- **Policy**: Maintainers → steering committee
- **Strategic**: Steering committee

### Process
1. **Proposal**: Create GitHub issue/RFC
2. **Discussion**: Community feedback (1-2 weeks)
3. **Decision**: Appropriate authority level
4. **Implementation**: Assign and track

## Conflict Resolution

*Structured approach to resolving disputes and preventing conflicts within the community.*

### Process
1. **Direct discussion**: Parties attempt resolution
2. **Maintainer mediation**: Neutral maintainer facilitates
3. **Steering committee**: Final arbitration
4. **Community input**: Public discussion if needed

### Prevention
- Clear guidelines and expectations
- Regular community meetings
- Transparent decision making
- Code of conduct enforcement

## Policy Updates

*How governance policies are updated to evolve with community needs and learnings.*

**Process:**
1. **RFC**: Propose changes via GitHub issue
2. **Community review**: 2-week feedback period
3. **Steering committee approval**: Majority vote required
4. **Implementation**: Update documentation and processes

**Criteria for updates:**
- Community needs evolution
- Process improvements
- Conflict resolution learnings
- External requirements changes

---

This governance model ensures quality, sustainability, and community collaboration while maintaining clear processes and expectations.

## Related Documentation

- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute components
- **[Onboarding Guide](ONBOARDING.md)** - Getting started as a contributor  
- **[Testing Guide](TESTING.md)** - Code quality and testing standards
- **[Best Practices Guide](BESTPRACTICES.md)** - Component development best practices *(coming soon)*
- **[Agents Guide](AGENTS.md)** - AI agent components and patterns *(coming soon)*

## Background

This governance model is based on [KEP-913: Components Repository](https://github.com/kubeflow/community/tree/master/proposals/913-components-repo), which established the framework for a curated collection of reusable Kubeflow Pipelines components with clear quality standards and community governance.

For questions about governance, contact the steering committee or open a GitHub issue.