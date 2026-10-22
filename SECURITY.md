# Security Policy

## Supported versions

Only the latest release and the current `main` branch receive security fixes during the alpha phase.

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could expose local source code, execute untrusted code, or compromise a publishing credential. Use GitHub's private vulnerability reporting feature for this repository when available.

Include:

- affected version or commit
- minimal reproduction
- impact and trust boundary
- suggested mitigation, when known

## Security model

ContextGraph performs static file reads and Python AST parsing. It does not import or execute indexed project modules. However:

- scanning untrusted repositories can consume CPU, memory, and disk I/O
- optional semantic models may require third-party package installation and model downloads
- generated context can contain secrets already present in source files

Run it with least privilege and exclude repositories or paths containing credentials that should not be included in exported model context.

The optional MCP server speaks stdio to a local client such as Claude Code or Cursor. It reads the project path named by a tool call and parses it with `ast`. It does not execute indexed code and it does not listen on a network port. A client that can invoke the server can read source the process can read, including secrets checked into those files. Do not expose the stdio process through an unauthenticated network proxy.
