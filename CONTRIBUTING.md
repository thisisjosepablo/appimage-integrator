# Contributing

Thanks for helping make AppImage Integrator safer and more useful.

## Before opening a pull request

1. Search existing issues and describe the user problem.
2. Keep the default workflow user-scoped; never require `sudo`.
3. Do not execute an AppImage as part of installation or CI.
4. Add tests for behavior changes and regression fixes.
5. Run `python -m unittest discover -s tests -v`.
6. Keep changes focused and document new options in the README.

Please do not commit third-party AppImages, private data, access tokens, or machine-specific paths. Small, reviewable pull requests are preferred.
