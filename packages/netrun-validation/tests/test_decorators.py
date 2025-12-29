"""Tests for validation decorators."""

import pytest
from netrun.validation.decorators import (
    validate_input,
    sanitize_output,
    validate_non_null,
    validate_type,
    validate_range_decorator,
)
from netrun.validation.validators import validate_non_empty


class TestValidateInput:
    """Tests for validate_input decorator."""

    def test_valid_input(self):
        """Test decorator with valid input."""
        @validate_input(validate_non_empty)
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        result = greet("Alice")
        assert result == "Hello, Alice!"

    def test_invalid_input(self):
        """Test decorator with invalid input."""
        @validate_input(validate_non_empty)
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        with pytest.raises(ValueError, match="value cannot be empty"):
            greet("")

    def test_multiple_validators(self):
        """Test decorator with multiple validators."""
        @validate_input(validate_non_empty, validate_non_empty)
        def create_user(name: str, email: str) -> dict:
            return {"name": name, "email": email}

        result = create_user("Alice", "alice@example.com")
        assert result["name"] == "Alice"

    def test_extra_args_no_validators(self):
        """Test decorator with more args than validators."""
        @validate_input(validate_non_empty)
        def create_user(name: str, age: int) -> dict:
            return {"name": name, "age": age}

        result = create_user("Alice", 30)
        assert result == {"name": "Alice", "age": 30}


class TestSanitizeOutput:
    """Tests for sanitize_output decorator."""

    def test_sanitize_dict(self):
        """Test sanitizing dictionary output."""
        @sanitize_output(["password", "secret"])
        def get_user() -> dict:
            return {"name": "Alice", "password": "secret123", "email": "alice@example.com"}

        result = get_user()
        assert result["password"] == "***REDACTED***"
        assert result["name"] == "Alice"
        assert result["email"] == "alice@example.com"

    def test_sanitize_list_of_dicts(self):
        """Test sanitizing list of dictionaries."""
        @sanitize_output(["password"])
        def get_users() -> list:
            return [
                {"name": "Alice", "password": "secret123"},
                {"name": "Bob", "password": "secret456"},
            ]

        result = get_users()
        assert result[0]["password"] == "***REDACTED***"
        assert result[1]["password"] == "***REDACTED***"
        assert result[0]["name"] == "Alice"

    def test_custom_replacement(self):
        """Test sanitization with custom replacement."""
        @sanitize_output(["password"], replacement="[HIDDEN]")
        def get_user() -> dict:
            return {"name": "Alice", "password": "secret123"}

        result = get_user()
        assert result["password"] == "[HIDDEN]"

    def test_non_dict_output(self):
        """Test decorator with non-dict output."""
        @sanitize_output(["password"])
        def get_name() -> str:
            return "Alice"

        result = get_name()
        assert result == "Alice"

    def test_list_of_non_dicts(self):
        """Test decorator with list of non-dicts."""
        @sanitize_output(["password"])
        def get_names() -> list:
            return ["Alice", "Bob"]

        result = get_names()
        assert result == ["Alice", "Bob"]


class TestValidateNonNull:
    """Tests for validate_non_null decorator."""

    def test_valid_args(self):
        """Test decorator with valid arguments."""
        @validate_non_null("name", "email")
        def create_user(name: str, email: str, age: int = None) -> dict:
            return {"name": name, "email": email, "age": age}

        result = create_user(name="Alice", email="alice@example.com")
        assert result["name"] == "Alice"

    def test_null_arg(self):
        """Test decorator with null argument."""
        @validate_non_null("name", "email")
        def create_user(name: str, email: str) -> dict:
            return {"name": name, "email": email}

        with pytest.raises(ValueError, match="Argument 'name' cannot be None"):
            create_user(name=None, email="alice@example.com")

    def test_optional_arg(self):
        """Test decorator allows optional arguments."""
        @validate_non_null("name")
        def create_user(name: str, age: int = None) -> dict:
            return {"name": name, "age": age}

        result = create_user(name="Alice", age=None)
        assert result["name"] == "Alice"
        assert result["age"] is None


class TestValidateType:
    """Tests for validate_type decorator."""

    def test_valid_types(self):
        """Test decorator with valid types."""
        @validate_type(name=str, age=int)
        def create_user(name: str, age: int) -> dict:
            return {"name": name, "age": age}

        result = create_user(name="Alice", age=30)
        assert result == {"name": "Alice", "age": 30}

    def test_invalid_type(self):
        """Test decorator with invalid type."""
        @validate_type(name=str, age=int)
        def create_user(name: str, age: int) -> dict:
            return {"name": name, "age": age}

        with pytest.raises(TypeError, match="Argument 'age' must be of type"):
            create_user(name="Alice", age="30")

    def test_none_value_allowed(self):
        """Test decorator allows None values."""
        @validate_type(name=str)
        def create_user(name: str, age: int = None) -> dict:
            return {"name": name, "age": age}

        result = create_user(name="Alice", age=None)
        assert result["age"] is None


class TestValidateRangeDecorator:
    """Tests for validate_range_decorator."""

    def test_valid_range(self):
        """Test decorator with value in range."""
        @validate_range_decorator("temperature", min_val=0.0, max_val=2.0)
        def set_temperature(temperature: float) -> float:
            return temperature

        result = set_temperature(temperature=0.7)
        assert result == 0.7

    def test_below_min(self):
        """Test decorator with value below minimum."""
        @validate_range_decorator("temperature", min_val=0.0, max_val=2.0)
        def set_temperature(temperature: float) -> float:
            return temperature

        with pytest.raises(ValueError, match="temperature must be at least 0.0"):
            set_temperature(temperature=-0.1)

    def test_above_max(self):
        """Test decorator with value above maximum."""
        @validate_range_decorator("temperature", min_val=0.0, max_val=2.0)
        def set_temperature(temperature: float) -> float:
            return temperature

        with pytest.raises(ValueError, match="temperature must be at most 2.0"):
            set_temperature(temperature=3.0)

    def test_min_only(self):
        """Test decorator with minimum only."""
        @validate_range_decorator("count", min_val=1)
        def set_count(count: int) -> int:
            return count

        result = set_count(count=100)
        assert result == 100

    def test_max_only(self):
        """Test decorator with maximum only."""
        @validate_range_decorator("count", max_val=100)
        def set_count(count: int) -> int:
            return count

        result = set_count(count=50)
        assert result == 50
