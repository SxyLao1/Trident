# Trident Memory Shell Detection Toolkit

> **v1.9.5**: Reference implementations and integration adapters for memory shell detection.

This directory contains third-party memory shell detection tools bundled as reference implementations. These are standalone diagnostic scripts (JSP/ASPX) that can be deployed to suspect web servers for incident response.

## Directory Structure

```
tools/memory-shell/
├── README.md                          ← This file
├── java/
│   ├── tomcat-memshell-scanner.jsp    ← c0ny1/java-memshell-scanner (JSP script)
│   └── README_upstream.md            ← Original README
└── aspnet/
    ├── aspx-memshell-scanner.aspx     ← yzddmr6/As-Exploits (ASPX script)
    └── README_upstream.md            ← Original README
```

## Upstream Sources

| Tool | Author | Repository | License |
|------|--------|------------|---------|
| tomcat-memshell-scanner.jsp | c0ny1 | https://github.com/c0ny1/java-memshell-scanner | Open Source |
| aspx-memshell-scanner.aspx | yzddmr6 | https://github.com/yzddmr6/As-Exploits | Open Source |

## Recommended Additional Tools

These tools are NOT bundled but are recommended for production incident response:

| Tool | Description | License |
|------|-------------|---------|
| [private-xss/memory-shell-detector](https://github.com/private-xss/memory-shell-detector) | GUI + CLI Java memshell detector, Tomcat/Jetty/WebLogic/Spring | MIT ✅ |
| [4ra1n/shell-analyzer](https://github.com/4ra1n/shell-analyzer) | GUI JVM monitor with one-click decompile & kill | Open Source |
| [y1shiny1shin/KMBA](https://github.com/y1shiny1shin/KMBA) | Arthas-based memshell killer, 12 types, Web UI + CLI | Open Source |

## Usage with Trident

Trident's `plugins/memory_shell_scanner.py` plugin can orchestrate these tools:
1. Auto-deploy the appropriate scanner script to the target web server
2. Fetch scan results via HTTP
3. Parse and ingest findings into Trident's detection pipeline
4. Correlate memory shell findings with file-system WebShell detections

### Manual Usage

```bash
# Deploy to Tomcat
cp tomcat-memshell-scanner.jsp /path/to/tomcat/webapps/ROOT/
curl http://target:8080/tomcat-memshell-scanner.jsp

# Deploy to IIS/ASP.NET
copy aspx-memshell-scanner.aspx C:\inetpub\wwwroot\
curl http://target/aspx-memshell-scanner.aspx
```

## License & Attribution

These tools are distributed under their original licenses. Trident does not claim authorship of any files in this directory except this README. See each subdirectory's `README_upstream.md` for original documentation and authorship.

If you use Trident in academic or commercial work, please cite the original tool authors in addition to Trident.
