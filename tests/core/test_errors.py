"""Tests for the Afanes domain exception hierarchy."""

import builtins

import afanes.core.errors


class TestExceptionHierarchy:
    def test_every_error_inherits_from_afanes_error(self) -> None:
        names = [
            "ConfigurationError",
            "VaultError",
            "VaultPathError",
            "NoteParseError",
            "EmptyCaptureError",
            "InvalidReferenceError",
            "NameCollisionError",
            "ReferenceRewriteError",
        ]
        for name in names:
            error_type = getattr(afanes.core.errors, name)
            assert issubclass(error_type, afanes.core.errors.AfanesError)

    def test_specific_errors_keep_their_parent(self) -> None:
        assert issubclass(afanes.core.errors.VaultPathError, afanes.core.errors.VaultError)

    def test_no_error_reuses_a_builtin_name(self) -> None:
        public_names = [
            name
            for name in vars(afanes.core.errors)
            if isinstance(getattr(afanes.core.errors, name), type)
            and issubclass(getattr(afanes.core.errors, name), BaseException)
            and getattr(afanes.core.errors, name).__module__ == afanes.core.errors.__name__
        ]
        assert all(not hasattr(builtins, name) for name in public_names)
