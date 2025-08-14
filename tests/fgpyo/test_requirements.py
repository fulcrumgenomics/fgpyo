import pytest

from fgpyo import RequirementError
from fgpyo import require


def test_require() -> None:
    """Require the requirements."""
    require(True)


def test_require_raises() -> None:
    """Require the requirements."""
    with pytest.raises(RequirementError) as excinfo:
        require(False)

    assert str(excinfo.value) == ""


def test_require_raises_with_message() -> None:
    """Require the requirements."""
    with pytest.raises(RequirementError, match="Message!") as excinfo:
        require(False, message="Message!")

    assert str(excinfo.value) == "Message!"


def test_require_raises_with_message_callable() -> None:
    with pytest.raises(RequirementError, match="Message!") as excinfo:
        require(False, message=lambda: "Message!")

    assert str(excinfo.value) == "Message!"
