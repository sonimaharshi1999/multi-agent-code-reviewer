# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Abstract base agent with shared AST utilities."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from typing import Optional

from src.message_bus import MessageBus
from src.models import AgentRole, FileAnalysis, Finding, Message, ReviewProfile
from src.providers.base import LLMProvider


class BaseAgent(ABC):
    """Base class for all review agents.

    Provides shared AST parsing, message-bus integration, and an
    optional LLM provider hook.
    """

    role: AgentRole

    def __init__(
        self,
        bus: MessageBus,
        profile: ReviewProfile = ReviewProfile.STANDARD,
        llm: Optional[LLMProvider] = None,
    ) -> None:
        self._bus = bus
        self._profile = profile
        self._llm = llm
        self._bus.subscribe("review_file", self._on_review_file, agent_role=self.role)

    # ------------------------------------------------------------------
    # AST helpers
    # ------------------------------------------------------------------

    @staticmethod
    def parse_ast(source: str) -> tuple[Optional[ast.Module], list[str]]:
        """Parse Python source into an AST.

        Returns:
            Tuple of (AST module or None, list of parse error strings).
        """
        errors: list[str] = []
        try:
            tree = ast.parse(source)
            return tree, errors
        except SyntaxError as exc:
            errors.append(f"SyntaxError at line {exc.lineno}: {exc.msg}")
            return None, errors

    @staticmethod
    def walk_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """Yield all function/async-function definitions in the AST."""
        return [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

    @staticmethod
    def walk_classes(tree: ast.Module) -> list[ast.ClassDef]:
        """Yield all class definitions."""
        return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    @staticmethod
    def walk_calls(tree: ast.Module) -> list[ast.Call]:
        """Yield all function call nodes."""
        return [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

    @staticmethod
    def walk_imports(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
        """Yield all import statements."""
        return [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

    @staticmethod
    def get_call_name(call: ast.Call) -> str:
        """Best-effort extraction of a call's function name."""
        func = call.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""

    @staticmethod
    def get_full_call_name(call: ast.Call) -> str:
        """Extract the full dotted name of a call (e.g. 'os.system')."""
        func = call.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parts: list[str] = [func.attr]
            node = func.value
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        return ""

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    def _on_review_file(self, message: Message) -> None:
        """Handle incoming review_file messages."""
        file_analysis: FileAnalysis = FileAnalysis(**message.payload["file_analysis"])
        findings = self.analyze(file_analysis)
        self._bus.publish(
            Message(
                sender=self.role,
                recipient=AgentRole.ORCHESTRATOR,
                msg_type="findings",
                payload={
                    "file_path": file_analysis.file_path,
                    "findings": [f.model_dump(mode="json") for f in findings],
                },
            )
        )

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    @abstractmethod
    def analyze(self, file_analysis: FileAnalysis) -> list[Finding]:
        """Run agent-specific analysis on a file.

        Args:
            file_analysis: Parsed file context.

        Returns:
            List of findings.
        """
        ...

    @property
    def profile_depth(self) -> int:
        """Numeric depth: quick=1, standard=2, thorough=3."""
        return {
            ReviewProfile.QUICK: 1,
            ReviewProfile.STANDARD: 2,
            ReviewProfile.THOROUGH: 3,
        }[self._profile]
