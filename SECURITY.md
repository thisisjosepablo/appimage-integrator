# Security policy

AppImages are executable programs. Only integrate files from sources you trust.

## Design safeguards

- The normal install path never launches the application or calls `--appimage-extract`.
- No root privileges are required.
- Copying is the default; moving is opt-in.
- Uninstall is constrained to paths recorded in the local manifest and expected managed directories.
- Remote downloads and self-updates are out of scope for the initial release.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the repository owner before publishing exploit details. Include the affected version, impact, and minimal reproduction steps. Do not attach potentially malicious binaries to a public issue.
