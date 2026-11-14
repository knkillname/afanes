"""Tests for the Afanes domain exception hierarchy."""

import builtins

import pytest

import afanes.core.errors
import afanes.i18n.messages


class TestExceptionHierarchy:
    def test_every_error_inherits_from_afanes_error(self) -> None:
        names = [
            "ConfigurationError",
            "VaultError",
            "VaultPathError",
            "VaultMissingError",
            "VaultNotDirectoryError",
            "VaultUnreadableError",
            "VaultNotEmptyError",
            "NoteParseError",
            "EmptyCaptureError",
            "InvalidReferenceError",
            "NameCollisionError",
            "ReferenceRewriteError",
            "RetiredValueError",
            "RetiredReferenceSchemeError",
            "StepMetadataError",
        ]
        for name in names:
            error_type = getattr(afanes.core.errors, name)
            assert issubclass(error_type, afanes.core.errors.AfanesError)

    def test_specific_errors_keep_their_parent(self) -> None:
        assert issubclass(afanes.core.errors.VaultPathError, afanes.core.errors.VaultError)
        assert issubclass(afanes.core.errors.VaultMissingError, afanes.core.errors.VaultError)
        assert issubclass(afanes.core.errors.VaultNotDirectoryError, afanes.core.errors.VaultError)
        assert issubclass(afanes.core.errors.VaultUnreadableError, afanes.core.errors.VaultError)
        assert issubclass(afanes.core.errors.VaultNotEmptyError, afanes.core.errors.VaultError)
        assert issubclass(afanes.core.errors.RetiredValueError, afanes.core.errors.NoteParseError)
        assert issubclass(afanes.core.errors.RetiredReferenceSchemeError, afanes.core.errors.InvalidReferenceError)

    def test_retired_value_message_names_the_replacement(self) -> None:
        error = afanes.core.errors.RetiredValueError(
            afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.RETIRED_ACTION_TYPE)
        )

        assert "one-step project" in afanes.i18n.messages.MessageCatalog.english().render(error.domain_message)

    def test_retired_scheme_message_names_the_replacement(self) -> None:
        error = afanes.core.errors.RetiredReferenceSchemeError(
            afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.RETIRED_PERSON_SCHEME)
        )

        assert "note:Name" in afanes.i18n.messages.MessageCatalog.english().render(error.domain_message)

    def test_no_error_reuses_a_builtin_name(self) -> None:
        public_names = [
            name
            for name in vars(afanes.core.errors)
            if isinstance(getattr(afanes.core.errors, name), type)
            and issubclass(getattr(afanes.core.errors, name), BaseException)
            and getattr(afanes.core.errors, name).__module__ == afanes.core.errors.__name__
        ]
        assert all(not hasattr(builtins, name) for name in public_names)


class TestDomainMessage:
    def test_a_message_preserves_value_order(self) -> None:
        message = afanes.core.errors.DomainMessage.of(
            afanes.core.errors.MessageCode.SETTINGS_VERSION_UNSUPPORTED,
            source="settings.json",
            version="2",
        )

        assert message.values == (("source", "settings.json"), ("version", "2"))

    def test_a_message_is_immutable(self) -> None:
        message = afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.SETTINGS_READ_FAILED)

        with pytest.raises(AttributeError):
            message.code = afanes.core.errors.MessageCode.SETTINGS_WRITE_FAILED  # type: ignore[misc]

    def test_the_technical_rendering_is_stable(self) -> None:
        message = afanes.core.errors.DomainMessage.of(
            afanes.core.errors.MessageCode.SETTINGS_VERSION_UNSUPPORTED,
            source="settings.json",
            version="2",
        )

        assert str(message) == "settings-version-unsupported: source=settings.json, version=2"

    def test_a_message_without_values_renders_the_code(self) -> None:
        message = afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.SETTINGS_READ_FAILED)

        assert str(message) == "settings-read-failed"

    def test_a_string_code_cannot_be_constructed(self) -> None:
        with pytest.raises(TypeError):
            afanes.core.errors.DomainMessage(code="settings-read-failed")  # type: ignore[arg-type]

    def test_a_repeated_placeholder_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="placeholder repeats"):
            afanes.core.errors.DomainMessage(
                code=afanes.core.errors.MessageCode.SETTINGS_READ_FAILED,
                values=(("source", "a"), ("source", "b")),
            )

    def test_an_empty_placeholder_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            afanes.core.errors.DomainMessage(
                code=afanes.core.errors.MessageCode.SETTINGS_READ_FAILED,
                values=(("", "a"),),
            )

    def test_a_non_text_value_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be text"):
            afanes.core.errors.DomainMessage(
                code=afanes.core.errors.MessageCode.SETTINGS_READ_FAILED,
                values=(("source", 2),),  # type: ignore[arg-type]
            )
