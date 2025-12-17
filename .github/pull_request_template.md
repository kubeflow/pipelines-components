**Description of your changes:**

**Checklist:**

### Pre-Submission Checklist

- [ ] All tests and CI checks pass
- [ ] Pre-commit hooks pass without errors
- [ ] You have [signed off your commits](https://www.kubeflow.org/docs/about/contributing/#sign-off-your-commits)
- [ ] The title for your pull request (PR) should follow our title convention.
  [Learn more about the pull request title convention used in this repository](https://github.com/kubeflow/pipelines/blob/master/CONTRIBUTING.md#pull-request-title-convention).

### Additional Checklist Items for New or Updated Components/Pipelines

- [ ] `metadata.yaml` includes fresh `lastVerified` timestamp
- [ ] All [required files](https://github.com/kubeflow/pipelines-components/blob/main/docs/CONTRIBUTING.md#required-files)
  are present and complete
- [ ] OWNERS file lists appropriate maintainers
- [ ] README provides clear documentation with usage examples
- [ ] Component follows `snake_case` naming convention
- [ ] No security vulnerabilities in dependencies
- [ ] Containerfile included if using a custom base image

<!--
   PR titles examples:
    * `fix(pipelines): fixes pipeline `my-pipeline` issue due to xyz. Fixes #1234`
       Use `fix` to indicate that this PR fixes a bug.
    * `feat(components): Add new component `my_component`. Fixes #1234, fixes #1235`
       Use `feat` to indicate that this PR adds a new feature.
    * `chore: set up changelog generation tools`
       Use `chore` to indicate that this PR makes some changes that users don't need to know.
    * `test: fix CI failure. Part of #1234`
        Use `part of` to indicate that a PR is working on an issue, but shouldn't close the issue when merged.
-->
