# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""SecurityAgent -- detects common vulnerability patterns via AST."""

from __future__ import annotations

import ast
from typing import Optional

from src.agents.base import BaseAgent
from src.message_bus import MessageBus
from src.models import AgentRole, FileAnalysis, Finding, ReviewProfile, Severity
from src.providers.base import LLMProvider

# Dangerous built-in calls
_DANGEROUS_CALLS: dict[str, tuple[Severity, str]] = {
    "eval": (Severity.CRITICAL, "Use of eval() can execute arbitrary code"),
    "exec": (Severity.CRITICAL, "Use of exec() can execute arbitrary code"),
    "compile": (Severity.HIGH, "compile() combined with exec/eval is dangerous"),
    "__import__": (Severity.HIGH, "Dynamic import via __import__ can load malicious modules"),
}

# Dangerous module-level calls (dotted names)
_DANGEROUS_MODULE_CALLS: dict[str, tuple[Severity, str]] = {
    "os.system": (Severity.CRITICAL, "os.system() is vulnerable to shell injection"),
    "os.popen": (Severity.HIGH, "os.popen() is vulnerable to shell injection"),
    "subprocess.call": (Severity.MEDIUM, "subprocess.call with shell=True risks injection"),
    "subprocess.Popen": (Severity.MEDIUM, "subprocess.Popen with shell=True risks injection"),
    "pickle.loads": (Severity.HIGH, "Unpickling untrusted data can execute arbitrary code"),
    "pickle.load": (Severity.HIGH, "Unpickling untrusted data can execute arbitrary code"),
    "yaml.load": (Severity.MEDIUM, "yaml.load without Loader= can execute arbitrary code"),
    "marshal.loads": (Severity.HIGH, "marshal.loads on untrusted data is dangerous"),
    "shelve.open": (Severity.MEDIUM, "shelve uses pickle internally -- untrusted data risk"),
    "tempfile.mktemp": (Severity.MEDIUM, "mktemp is vulnerable to race conditions; use mkstemp"),
}

# Hardcoded secret patterns (variable names)
_SECRET_PATTERNS: list[str] = [
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "token",
    "private_key",
]


class SecurityAgent(BaseAgent):
    """Detects security vulnerabilities via AST pattern matching.

    Checks for:
    - Dangerous function calls (eval, exec, os.system, etc.)
    - Hardcoded secrets / credentials
    - SQL injection patterns (string formatting in queries)
    - Insecure imports
    - Shell injection risks
    """

    role = AgentRole.SECURITY

    def __init__(
        self,
        bus: MessageBus,
        profile: ReviewProfile = ReviewProfile.STANDARD,
        llm: Optional[LLMProvider] = None,
    ) -> None:
        super().__init__(bus, profile, llm)

    def analyze(self, file_analysis: FileAnalysis) -> list[Finding]:
        """Run security analysis on a file."""
        findings: list[Finding] = []
        tree, errors = self.parse_ast(file_analysis.source_code)
        if tree is None:
            return findings

        findings.extend(self._check_dangerous_calls(tree, file_analysis.file_path))
        findings.extend(self._check_hardcoded_secrets(tree, file_analysis.file_path))
        findings.extend(self._check_sql_injection(tree, file_analysis.file_path))

        if self.profile_depth >= 2:
            findings.extend(self._check_insecure_imports(tree, file_analysis.file_path))
            findings.extend(self._check_shell_true(tree, file_analysis.file_path))

        if self.profile_depth >= 3:
            findings.extend(self._check_assert_usage(tree, file_analysis.file_path))

        return findings

    def _check_dangerous_calls(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Flag dangerous built-in and module-level calls."""
        findings: list[Finding] = []
        for call in self.walk_calls(tree):
            name = self.get_call_name(call)
            full_name = self.get_full_call_name(call)

            if name in _DANGEROUS_CALLS:
                sev, desc = _DANGEROUS_CALLS[name]
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=sev,
                        title=f"Dangerous call: {name}()",
                        description=desc,
                        file_path=file_path,
                        line_number=call.lineno,
                        category="dangerous_call",
                        suggestion=f"Avoid {name}(). Use safer alternatives.",
                    )
                )

            if full_name in _DANGEROUS_MODULE_CALLS:
                sev, desc = _DANGEROUS_MODULE_CALLS[full_name]
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=sev,
                        title=f"Dangerous call: {full_name}()",
                        description=desc,
                        file_path=file_path,
                        line_number=call.lineno,
                        category="dangerous_call",
                        suggestion=f"Use a safer alternative to {full_name}().",
                    )
                )
        return findings

    def _check_hardcoded_secrets(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Detect hardcoded secrets assigned to suspicious variable names."""
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_lower = target.id.lower()
                        if any(pat in var_lower for pat in _SECRET_PATTERNS):
                            if isinstance(node.value, ast.Constant) and isinstance(
                                node.value.value, str
                            ):
                                if len(node.value.value) > 0:
                                    findings.append(
                                        Finding(
                                            agent=self.role,
                                            severity=Severity.HIGH,
                                            title=f"Hardcoded secret: {target.id}",
                                            description=(
                                                f"Variable '{target.id}' appears to contain "
                                                "a hardcoded secret or credential."
                                            ),
                                            file_path=file_path,
                                            line_number=node.lineno,
                                            category="hardcoded_secret",
                                            suggestion="Use environment variables or a secrets manager.",
                                        )
                                    )
        return findings

    def _check_sql_injection(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Detect f-string or %-format SQL query construction."""
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and "query" in target.id.lower():
                        if isinstance(node.value, (ast.JoinedStr, ast.BinOp)):
                            findings.append(
                                Finding(
                                    agent=self.role,
                                    severity=Severity.HIGH,
                                    title="Potential SQL injection",
                                    description=(
                                        f"Variable '{target.id}' builds a SQL query via "
                                        "string interpolation, risking SQL injection."
                                    ),
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    category="sql_injection",
                                    suggestion="Use parameterized queries instead.",
                                )
                            )
        return findings

    def _check_insecure_imports(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Flag imports of known-insecure modules."""
        insecure = {"telnetlib", "ftplib", "xmlrpc"}
        findings: list[Finding] = []
        for imp in self.walk_imports(tree):
            names: list[str] = []
            if isinstance(imp, ast.Import):
                names = [alias.name for alias in imp.names]
            elif isinstance(imp, ast.ImportFrom) and imp.module:
                names = [imp.module]
            for name in names:
                root = name.split(".")[0]
                if root in insecure:
                    findings.append(
                        Finding(
                            agent=self.role,
                            severity=Severity.LOW,
                            title=f"Insecure module: {root}",
                            description=f"Module '{root}' uses unencrypted protocols.",
                            file_path=file_path,
                            line_number=imp.lineno,
                            category="insecure_import",
                            suggestion=f"Use a secure alternative to {root}.",
                        )
                    )
        return findings

    def _check_shell_true(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Detect subprocess calls with shell=True."""
        findings: list[Finding] = []
        for call in self.walk_calls(tree):
            full_name = self.get_full_call_name(call)
            if "subprocess" in full_name:
                for kw in call.keywords:
                    if kw.arg == "shell":
                        if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            findings.append(
                                Finding(
                                    agent=self.role,
                                    severity=Severity.HIGH,
                                    title="subprocess with shell=True",
                                    description=(
                                        f"{full_name}() called with shell=True. "
                                        "This is vulnerable to shell injection."
                                    ),
                                    file_path=file_path,
                                    line_number=call.lineno,
                                    category="shell_injection",
                                    suggestion="Pass a list of arguments instead of shell=True.",
                                )
                            )
        return findings

    def _check_assert_usage(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Flag assert statements that might be used for security checks."""
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.INFO,
                        title="Assert used (may be stripped with -O)",
                        description=(
                            "assert statements are removed when Python runs with "
                            "optimization (-O). Do not rely on them for security."
                        ),
                        file_path=file_path,
                        line_number=node.lineno,
                        category="assert_security",
                        suggestion="Use explicit if/raise for security-critical checks.",
                    )
                )
        return findings
