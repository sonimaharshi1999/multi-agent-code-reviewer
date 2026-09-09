# Multi-Agent Code Review System -- Test Fixture
# Author: Maharshi Soni | License: MIT
"""Synthetic clean code that should produce minimal findings."""

from typing import Optional


class UserProfile:
    """Represents a user profile."""

    def __init__(self, name: str, email: str) -> None:
        self.name = name
        self.email = email

    def display_name(self) -> str:
        """Return the display name."""
        return self.name.strip().title()

    def is_valid(self) -> bool:
        """Check if the profile has required fields."""
        return bool(self.name and self.email)


def greet(user: Optional[UserProfile] = None) -> str:
    """Greet a user by name.

    Args:
        user: The user profile, or None for a generic greeting.

    Returns:
        A greeting string.
    """
    if user is None:
        return "Hello, stranger!"
    return f"Hello, {user.display_name()}!"


def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b
