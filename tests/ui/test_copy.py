"""Copy gate for the interface writing style.

The gate scans the interface and command-line copy catalogs. Mechanical rules
apply to every string literal; capitalization rules apply to the constants and
mapping values declared in the classification sets. The gate has no baseline:
every copy violation must be fixed, never recorded.
"""

import ast
import re
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "afanes"
CATALOGS = ("ui/strings.py", "cli/strings.py")
ELLIPSIS = "…"
STRAIGHT_APOSTROPHE = "'"
THREE_DOTS = "..."
TRAILING_PERIOD = re.compile(r"\.\s*$")
BANNED_PRONOUNS = re.compile(r"\b(?:I|me|my|mine|we|us|our|ours|you|your|yours)\b", re.IGNORECASE)
WORD_CHARACTERS = re.compile(r"[A-Za-z]")
TRIM_CHARACTERS = ".,;:!?()[]“”\"'"
LONG_WORD_LENGTH = 4
SMALL_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "from",
        "in",
        "nor",
        "of",
        "off",
        "on",
        "or",
        "per",
        "so",
        "the",
        "to",
        "up",
        "via",
        "vs",
        "with",
        "yet",
    }
)

HEADER_CASE = frozenset(
    {
        "ABOUT_ACTION",
        "ABOUT_TITLE",
        "ABOUT_VERSION",
        "APP_TITLE",
        "BROWSER_CREATE_ACTION",
        "BROWSER_FAILURES",
        "BROWSER_NEW_REFERENCE",
        "BROWSER_NEW_REFERENCE_TITLE",
        "BROWSER_SEARCH_CLEAR",
        "BROWSER_SEARCH_TITLE",
        "BROWSER_TEMPLATE_EMPTY",
        "CANCEL_ACTION",
        "CAPTURE_ACTION",
        "CHANGE_VAULT_CREATE",
        "CHANGE_VAULT_DIALOG_TITLE",
        "CHANGE_VAULT_OPEN",
        "CLOSE_ACTION",
        "CLOSE_NAVIGATION",
        "CLOSE_VAULT_ACTION",
        "COMPOSER_LABEL",
        "EMPTY_TITLE",
        "INBOX_TITLE",
        "LOG_CARD_EMPTY",
        "LOG_CREATE_ACTION",
        "LOG_ENTRY_TITLE",
        "LOG_MODE_ENTRIES",
        "LOG_MODE_EVERYTHING",
        "LOG_NEXT_MONTH",
        "LOG_PREVIOUS_MONTH",
        "LOG_TODAY_ENTRY",
        "LOG_UNDATED",
        "MAIN_MENU",
        "NEW_CAPTURE_ACTION",
        "NEW_VAULT_ACTION",
        "NEW_VAULT_BROWSE",
        "NEW_VAULT_CREATE",
        "NEW_VAULT_DIALOG_TITLE",
        "NEW_VAULT_PICKER_TITLE",
        "NEW_VAULT_TEMPLATE_NONE",
        "PAGE_ACTIONS",
        "PAGE_AMBIGUOUS_TITLE",
        "PAGE_ASKED_BY_SET",
        "PAGE_BACK",
        "PAGE_CANCEL",
        "PAGE_CATEGORY_MOVE_CONFIRM",
        "PAGE_CATEGORY_MOVE_TITLE",
        "PAGE_CONFLICT_DISCARD",
        "PAGE_CONFLICT_OVERWRITE",
        "PAGE_CONFLICT_RECREATE",
        "PAGE_CONFLICT_RELOAD",
        "PAGE_CONFLICT_TITLE",
        "PAGE_CONNECTIONS_LINKED_FROM",
        "PAGE_CONNECTIONS_OWNED_PROJECTS",
        "PAGE_CONNECTIONS_OWNED_STEPS",
        "PAGE_CONNECTIONS_REQUESTED_PROJECTS",
        "PAGE_CONNECTIONS_SHOW_COMPLETED_STEPS",
        "PAGE_CONNECTIONS_SHOW_FINISHED_PROJECTS",
        "PAGE_CONNECTIONS_TITLE",
        "PAGE_DONE",
        "PAGE_EDIT",
        "PAGE_NEW",
        "PAGE_NONE",
        "PAGE_OWNER_SET",
        "PAGE_PROJECT_DUE_ADD",
        "PAGE_PROJECT_DUE_CLEAR",
        "PAGE_RAW_SAVE",
        "PAGE_REPAIR_CANCEL",
        "PAGE_REPAIR_KEEP",
        "PAGE_REPAIR_REWRITE",
        "PAGE_REPAIR_TITLE",
        "PAGE_RENAME",
        "PAGE_RENAME_CONFIRM",
        "PAGE_RENAME_PREVIEW_ACTION",
        "PAGE_RENAME_TITLE",
        "PAGE_SAVED",
        "PAGE_SAVING",
        "PAGE_STEP_CLEAR_PLAN",
        "PAGE_STEP_OWNER_ACTION",
        "PAGE_STEP_OWNER_ADD",
        "PAGE_STEP_OWNER_REMOVE",
        "PAGE_STEP_OWNER_TITLE",
        "PAGE_STEP_PLAN_ACTION",
        "PAGE_STEP_TICK",
        "PAGE_STEP_UNTICK",
        "PAGE_STEP_WAITING",
        "PAGE_TRASH",
        "PAGE_TRASH_MOVED",
        "PAGE_TRASH_RESTORED",
        "PAGE_TYPE_CHANGE_CONFIRM",
        "PAGE_TYPE_CHANGE_TITLE",
        "PAGE_TYPE_LABELS",
        "PAGE_UNSAVED",
        "PREVIEW_TITLE",
        "PROCESS_ACTION",
        "PROCESSING_CANCEL_ACTION",
        "PROCESSING_CAPTURE",
        "PROCESSING_CONFIRM_ACTION",
        "PROCESSING_DONE_ACTION",
        "PROCESSING_OUTCOME_LABELS",
        "PROCESSING_PLAN_TITLE",
        "PROCESSING_PREVIEW_ACTION",
        "PROCESSING_STATUS_LABELS",
        "PROCESSING_SUCCESS_TITLE",
        "PROCESSING_TEMPLATE_EMPTY",
        "PROCESSING_TITLE",
        "PROJECT_GROUP_LABELS",
        "REFRESH_ACTION",
        "REVIEW_BACK_TO_BROWSER",
        "REVIEW_CANCEL",
        "REVIEW_CAPTURE_TITLE",
        "REVIEW_COMPLETE_TITLE",
        "REVIEW_CONFIRM",
        "REVIEW_CONFIRM_DEFER",
        "REVIEW_CONFIRM_DONE",
        "REVIEW_CREATE_STEP",
        "REVIEW_CURRENT",
        "REVIEW_DEFER",
        "REVIEW_DELEGATE",
        "REVIEW_DO_NOW",
        "REVIEW_DUE",
        "REVIEW_DUE_STEP_TITLE",
        "REVIEW_KIND_LABELS",
        "REVIEW_LAUNCH_DIGEST_ACTION",
        "REVIEW_MARK_DONE",
        "REVIEW_NEXT",
        "REVIEW_NEXT_STEP",
        "REVIEW_OPEN_ACTION",
        "REVIEW_OPEN_PROJECT",
        "REVIEW_OTHER_STEPS",
        "REVIEW_PENDING_MANY",
        "REVIEW_PENDING_ONE",
        "REVIEW_POSTPONE",
        "REVIEW_PROCESS_ACTION",
        "REVIEW_REASSIGN",
        "REVIEW_SKIP",
        "REVIEW_START_ACTION",
        "REVIEW_STEP_CANCEL",
        "REVIEW_STEP_CONFIRM",
        "REVIEW_TITLE",
        "REVIEW_WAITING_STEP_TITLE",
        "REVIEW_ZERO_TITLE",
        "ROLE_NAME_ASKED_BY_TITLE",
        "ROLE_NAME_CLEAR",
        "ROLE_NAME_OWNER_TITLE",
        "ROLE_NAME_SAVE",
        "ROLE_REFERENCE_CREATE",
        "ROLE_REFERENCE_NO_CATEGORY",
        "ROLE_REFERENCE_TITLE",
        "SESSION_ACTIVE_TITLE",
        "SESSION_RETRY",
        "TRASH_DELETE_CONFIRM",
        "TRASH_DELETE_PERMANENTLY",
        "TRASH_DELETE_TITLE",
        "TRASH_DELETED",
        "TRASH_EMPTY_ACTION",
        "TRASH_EMPTY_CONFIRM",
        "TRASH_EMPTY_DONE",
        "TRASH_EMPTY_TITLE",
        "TRASH_OVERWRITE_CONFIRM",
        "TRASH_OVERWRITE_TITLE",
        "TRASH_RESTORE",
        "TRASH_ROW_FROM",
        "TRASH_TITLE",
        "UNDO_ACTION",
        "VAULT_SCHEMA_ADOPT_ACTION",
        "VAULT_SCHEMA_ADOPT_TITLE",
        "WELCOME_CHOOSE",
        "WELCOME_OPEN",
        "WELCOME_PICKER_TITLE",
        "WELCOME_TITLE",
        "WORKING",
        "WORKSPACE_NAVIGATION",
        "WORKSPACE_SECTION_LABELS",
    }
)

SENTENCE_CASE = frozenset(
    {
        "ABOUT_LICENSE",
        "ADOPT_COMMAND",
        "ADOPT_DIRECTORY_HELP",
        "ADOPT_FAILED",
        "ADOPT_HELP",
        "ADOPT_NO_REMEMBER_HELP",
        "ADOPT_REMEMBER_FAILED",
        "ADOPTED_VAULT",
        "ALREADY_VAULT",
        "BROWSER_CREATE_FAILED",
        "BROWSER_EMPTY",
        "BROWSER_NAME_LABEL",
        "BROWSER_NAME_REQUIRED",
        "BROWSER_NEW_REFERENCE_BODY",
        "BROWSER_NO_MATCH",
        "BROWSER_NO_MATCH_QUERY",
        "BROWSER_SEARCH_HINT",
        "BROWSER_TEMPLATE_DESCRIPTION_EMPTY",
        "BROWSER_TEMPLATE_INVALID",
        "BROWSER_TEMPLATE_LABEL",
        "BROWSER_TEMPLATE_NO_DESCRIPTION",
        "BROWSER_TEMPLATE_OPTION",
        "BROWSER_TEMPLATE_OPTION_DUPLICATE",
        "BROWSER_TEMPLATE_OPTION_DUPLICATE_PLAIN",
        "BROWSER_TEMPLATE_OPTION_PLAIN",
        "CAPTURE_EMPTY",
        "CAPTURE_FAILED",
        "CHANGE_VAULT_DIALOG_BODY",
        "COMPOSER_HINT",
        "CREATE_COMMAND",
        "CREATE_DIRECTORY_HELP",
        "CREATE_FAILED",
        "CREATE_HELP",
        "CREATED_PARENTS",
        "CREATED_VAULT",
        "DESCRIPTION",
        "EMPTY_BODY",
        "LAUNCH_DESCRIPTION",
        "LAUNCH_DESKTOP_FAILED",
        "LAUNCH_MISSING_DESKTOP",
        "LAUNCH_MISSING_SDK",
        "LAUNCH_MISSING_WEB",
        "LAUNCH_PORT_HELP",
        "LAUNCH_PORT_NOT_NUMBER",
        "LAUNCH_PORT_OUT_OF_RANGE",
        "LAUNCH_VAULT_HELP",
        "LAUNCH_VAULT_INVALID",
        "LAUNCH_WEB_HELP",
        "LOG_CARD_DESCRIPTION_EMPTY",
        "LOG_CARD_LABEL",
        "LOG_CREATE_FAILED",
        "LOG_EMPTY",
        "LOG_ENTRY_BODY",
        "LOG_MODE_NOT_REMEMBERED",
        "LOG_MONTH_ENTRY_MARK",
        "LOG_NEW_MONTH_ENTRY",
        "LOG_NEW_YEAR_ENTRY",
        "LOG_OPEN_MONTH_ENTRY",
        "LOG_OPEN_YEAR_ENTRY",
        "LOG_PLACEHOLDER",
        "LOG_TITLE_LABEL",
        "LOG_TITLE_REQUIRED",
        "LOG_YEAR_ENTRY_MARK",
        "NEW_VAULT_DIALOG_BODY",
        "NEW_VAULT_PATH_LABEL",
        "NEW_VAULT_PREVIEW_GUIDE",
        "NEW_VAULT_PREVIEW_TEMPLATE",
        "NEW_VAULT_TEMPLATE_FAILED",
        "NEW_VAULT_TEMPLATE_LABEL",
        "NEW_VAULT_TEMPLATE_OPTION",
        "NEW_VAULT_TEMPLATE_UNAVAILABLE",
        "NO_REMEMBER_HELP",
        "NOT_REMEMBERED",
        "NOTE_COUNT_MANY",
        "NOTE_COUNT_ONE",
        "PAGE_AMBIGUOUS_BODY",
        "PAGE_ASKED_BY_HINT",
        "PAGE_ASKED_BY_LABEL",
        "PAGE_BODY_LABEL",
        "PAGE_CATEGORY_HINT",
        "PAGE_CATEGORY_INVALID",
        "PAGE_CATEGORY_LABEL",
        "PAGE_CATEGORY_MOVE_BODY",
        "PAGE_CATEGORY_MOVE_FAILED",
        "PAGE_CONFLICT_CHANGED",
        "PAGE_CONFLICT_LEAVE",
        "PAGE_CONFLICT_MISSING",
        "PAGE_DATE",
        "PAGE_DATE_CHANGE_FAILED",
        "PAGE_DATE_CHANGE_PARTIAL",
        "PAGE_DATE_LABEL",
        "PAGE_DUE_DATE_LABEL",
        "PAGE_EMPTY",
        "PAGE_IDENTITY_LABEL",
        "PAGE_LOG_DATE_REQUIRED",
        "PAGE_NO_DATE",
        "PAGE_OPEN_FAILED",
        "PAGE_OWNER_HINT",
        "PAGE_OWNER_LABEL",
        "PAGE_PATH_LABEL",
        "PAGE_PENDING_DIALOG",
        "PAGE_PROJECT_EMPTY_BODY",
        "PAGE_PROJECT_NO_DUE",
        "PAGE_PROJECT_NO_STATUS",
        "PAGE_RAW_UPGRADED",
        "PAGE_RAW_WARNING",
        "PAGE_REPAIR_BODY",
        "PAGE_REPAIR_COUNT",
        "PAGE_REPAIR_FAILED",
        "PAGE_REPAIR_PARTIAL",
        "PAGE_REPAIR_PENDING",
        "PAGE_RENAME_FAILED",
        "PAGE_RENAME_LABEL",
        "PAGE_RENAME_PARTIAL",
        "PAGE_RENAME_PREVIEW",
        "PAGE_REWRITE_CHANGED_ON_DISK",
        "PAGE_REWRITE_NONE",
        "PAGE_REWRITE_NOT_UPDATED",
        "PAGE_REWRITE_PROBLEM",
        "PAGE_REWRITE_UPDATED",
        "PAGE_SAVE_FAILED",
        "PAGE_STATUS_LABEL",
        "PAGE_STEP_ACTUAL",
        "PAGE_STEP_FAILED",
        "PAGE_STEP_OWNER_DUPLICATE",
        "PAGE_STEP_OWNER_HINT",
        "PAGE_STEP_OWNERS",
        "PAGE_STEP_OWNERS_LABEL",
        "PAGE_STEP_PLAN",
        "PAGE_STEP_TAGS",
        "PAGE_TRASH_FAILED",
        "PAGE_TRASH_RESTORE_FAILED",
        "PAGE_TYPE_CHANGE_BODY",
        "PAGE_TYPE_CHANGE_FAILED",
        "PAGE_TYPE_CHANGE_LEAVE",
        "PAGE_TYPE_CHANGE_PARTIAL",
        "PAGE_TYPE_LABEL",
        "PREVIEW_EMPTY",
        "PREVIEW_FAILED",
        "PROCESSING_DESTINATION",
        "PROCESSING_DUE_DATE_LABEL",
        "PROCESSING_EMPTY_OUTCOME",
        "PROCESSING_FAILED",
        "PROCESSING_INVALID_DATE",
        "PROCESSING_MISSING",
        "PROCESSING_OUTCOME_LABEL",
        "PROCESSING_PLAN_ASKED_BY",
        "PROCESSING_PLAN_CATEGORY",
        "PROCESSING_PLAN_FAILED",
        "PROCESSING_DESTINATION_TRASH",
        "PROCESSING_PLAN_OWNER",
        "PROCESSING_PLAN_SCAFFOLD",
        "PROCESSING_PROJECT_LABEL",
        "PROCESSING_SUCCESS_TRASH",
        "PROCESSING_READ_FAILED",
        "PROCESSING_REFERENCE_WARNING",
        "PROCESSING_REFRESH_FAILED",
        "PROCESSING_SCHEME_WARNING",
        "PROCESSING_STATUS_LABEL",
        "PROCESSING_SUCCESS_BODY",
        "PROCESSING_TEMPLATE_DESCRIPTION_EMPTY",
        "PROCESSING_TEMPLATE_INVALID",
        "PROCESSING_TEMPLATE_LABEL",
        "PROCESSING_TEMPLATE_NO_DESCRIPTION",
        "PROCESSING_TEMPLATE_OPTION",
        "PROCESSING_TEMPLATE_OPTION_DUPLICATE",
        "PROCESSING_TEMPLATE_OPTION_DUPLICATE_PLAIN",
        "PROCESSING_TEMPLATE_OPTION_PLAIN",
        "PROCESSING_UNRESOLVED",
        "PROGRAM",
        "PROJECT_DUE",
        "PROJECT_META_SEPARATOR",
        "PROJECT_NEXT_STEP",
        "PROJECT_NO_NEXT_STEP",
        "PROJECT_OPEN_STEPS_MANY",
        "PROJECT_OPEN_STEPS_ONE",
        "PROJECT_STATUS",
        "REFRESH_FAILED",
        "REMEMBERED",
        "REMEMBER_FAILED",
        "REVIEW_CAPTURE_READ_FAILED",
        "REVIEW_COMPLETE_BODY",
        "REVIEW_INVALID_DATE",
        "REVIEW_LAUNCH_DIGEST_MANY",
        "REVIEW_LAUNCH_DIGEST_ONE",
        "REVIEW_NO_NEXT_STEP",
        "REVIEW_OWNER_LABEL",
        "REVIEW_OWNER_REQUIRED",
        "REVIEW_POSTPONE_LABEL",
        "REVIEW_PROJECT_FAILED",
        "REVIEW_STEP_CREATED",
        "REVIEW_STEP_FAILED",
        "REVIEW_STEP_OWNERS",
        "REVIEW_STEP_TITLE_HINT",
        "REVIEW_STEP_TITLE_LABEL",
        "REVIEW_TITLE_REQUIRED",
        "REVIEW_ZERO_BODY",
        "ROLE_LINK_AMBIGUOUS",
        "ROLE_LINK_MISSING",
        "ROLE_NAME_BODY",
        "ROLE_NAME_HINT",
        "ROLE_NAME_LABEL",
        "ROLE_REFERENCE_BODY",
        "ROLE_REFERENCE_CATEGORY_HINT",
        "ROLE_REFERENCE_CATEGORY_LABEL",
        "SEEDED_FOLDERS",
        "SESSION_ACTIVE_BODY",
        "SETTINGS_FILE",
        "SETTINGS_UNREADABLE",
        "TEMPLATE_LINE",
        "TEMPLATE_NONE",
        "TEMPLATE_NOTES_MANY",
        "TEMPLATE_NOTES_ONE",
        "TEMPLATE_OPTION_HELP",
        "TEMPLATE_USED",
        "TEMPLATES_COMMAND",
        "TRASH_CONFIRM_LEAVE",
        "TRASH_DELETE_BODY",
        "TRASH_DELETE_FAILED",
        "TRASH_EMPTY",
        "TRASH_EMPTY_BODY",
        "TRASH_EMPTY_FAILED",
        "TRASH_ENTRY_MANY",
        "TRASH_ENTRY_ONE",
        "TRASH_INFO",
        "TRASH_INFO_NO_DATE",
        "TRASH_MAINTENANCE_FAILED",
        "TRASH_OPEN_FAILED",
        "TRASH_OVERWRITE_BODY",
        "TRASH_PAGE_GONE",
        "TRASH_RESTORE_FAILED",
        "TEMPLATES_FAILED",
        "TEMPLATES_HELP",
        "VAULT_COMMAND",
        "VAULT_CREATED_NOT_REMEMBERED",
        "VAULT_CLOSE_NOT_FORGOTTEN",
        "VAULT_HELP",
        "VAULT_MISSING",
        "VAULT_NOT_DIRECTORY",
        "VAULT_NOT_EMPTY",
        "VAULT_PATH_REQUIRED",
        "VAULT_SCHEMA_ADOPTED_NOT_REMEMBERED",
        "VAULT_SCHEMA_ADOPT_BODY",
        "VAULT_SCHEMA_ADOPT_MESSAGE",
        "VAULT_SCHEMA_NOT_ADOPTABLE",
        "VAULT_SCHEMA_UNAVAILABLE",
        "VAULT_SELECTION_FAILED",
        "VAULT_UNREADABLE",
        "WELCOME_BODY",
        "WELCOME_NOTE",
        "WELCOME_PATH_HINT",
        "WELCOME_PATH_LABEL",
        "WRITTEN_NOTES",
    }
)

ELLIPSIS_ACTIONS = frozenset(
    {
        "BROWSER_NEW_REFERENCE",
        "CHANGE_VAULT_CREATE",
        "CHANGE_VAULT_OPEN",
        "NEW_VAULT_ACTION",
        "NEW_VAULT_BROWSE",
        "PAGE_ASKED_BY_SET",
        "PAGE_OWNER_SET",
        "PAGE_PROJECT_DUE_ADD",
        "PAGE_RENAME",
        "PAGE_STEP_OWNER_ACTION",
        "PAGE_STEP_PLAN_ACTION",
        "PROCESS_ACTION",
        "REVIEW_CREATE_STEP",
        "REVIEW_DEFER",
        "REVIEW_DELEGATE",
        "REVIEW_MARK_DONE",
        "REVIEW_POSTPONE",
        "REVIEW_PROCESS_ACTION",
        "REVIEW_REASSIGN",
        "TRASH_DELETE_PERMANENTLY",
        "TRASH_EMPTY_ACTION",
        "WELCOME_CHOOSE",
    }
)


def catalog_entries(relative: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return the string constants and mapping values of one catalog.

    Parameters
    ----------
    relative : str
        Catalog path relative to ``src/afanes``.

    Returns
    -------
    tuple[dict[str, str], dict[str, list[str]]]
        Constant name to value, and mapping name to its string values.
    """
    tree = ast.parse((SOURCE_ROOT / relative).read_text(encoding="utf-8"))
    constants: dict[str, str] = {}
    mappings: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            constants[name] = value.value
        elif (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "MappingProxyType"
            and value.args
            and isinstance(value.args[0], ast.Dict)
        ):
            mappings[name] = [
                item.value
                for item in value.args[0].values
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
    return constants, mappings


def catalog_literals(relative: str) -> list[tuple[int, str]]:
    """Return every string literal in one catalog except docstrings.

    Parameters
    ----------
    relative : str
        Catalog path relative to ``src/afanes``.

    Returns
    -------
    list[tuple[int, str]]
        Line number and literal value.
    """
    tree = ast.parse((SOURCE_ROOT / relative).read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
    ]


def mechanical_violations(text: str) -> list[str]:
    """Return the mechanical writing-style violations in one string.

    Parameters
    ----------
    text : str
        Copy string to inspect.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the string conforms.
    """
    violations: list[str] = []
    if STRAIGHT_APOSTROPHE in text:
        violations.append("straight apostrophe")
    if THREE_DOTS in text:
        violations.append("three-dot ellipsis")
    elif TRAILING_PERIOD.search(text):
        violations.append("trailing period")
    if BANNED_PRONOUNS.search(text):
        violations.append("first- or second-person pronoun")
    return violations


def header_case_violations(text: str) -> list[str]:
    """Return the header-capitalization violations in one string.

    Parameters
    ----------
    text : str
        Header or short control label to inspect.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the string conforms.

    Notes
    -----
    Short content words are left to manual review because identifying nouns
    and verbs needs a lexicon the project does not maintain.
    """
    tokens = text.split()
    meaningful: list[int] = []
    for index, token in enumerate(tokens):
        cleaned = token.strip(TRIM_CHARACTERS)
        if WORD_CHARACTERS.search(cleaned) and not is_literal_token(cleaned):
            meaningful.append(index)
    if not meaningful:
        return []
    first, last = meaningful[0], meaningful[-1]
    violations: list[str] = []
    for index in meaningful:
        violations.extend(header_word_violations(index, tokens[index], first, last))
    return violations


def header_word_violations(index: int, token: str, first: int, last: int) -> list[str]:
    """Return the header-capitalization violations for one word.

    Parameters
    ----------
    index : int
        Position of the token in the label.
    token : str
        Token to inspect.
    first : int
        Position of the first meaningful token.
    last : int
        Position of the last meaningful token.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the token conforms.
    """
    cleaned = token.strip(TRIM_CHARACTERS)
    word = cleaned.lower()
    if index not in (first, last) and word in SMALL_WORDS:
        if cleaned[0].isupper():
            return [f"capitalized short word {cleaned!r}"]
        return []
    violations: list[str] = []
    if cleaned[0].islower():
        if index in (first, last):
            violations.append(f"lowercase edge word {cleaned!r}")
        elif len(cleaned) >= LONG_WORD_LENGTH:
            violations.append(f"lowercase long word {cleaned!r}")
    if "-" in cleaned:
        violations.extend(
            f"lowercase hyphen part {part!r}"
            for part in cleaned.split("-")
            if part and part[0].islower() and part.isalpha()
        )
    return violations


def sentence_case_violations(text: str) -> list[str]:
    """Return the sentence-capitalization violations in one string.

    Parameters
    ----------
    text : str
        Field label or prose string to inspect.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the string conforms.
    """
    stripped = text.lstrip()
    if not stripped or not WORD_CHARACTERS.search(stripped):
        return []
    if stripped[0] in "{0123456789":
        return []
    if " " not in stripped and stripped.islower():
        return []
    if stripped[0].isupper():
        return []
    return ["sentence does not start uppercase"]


def is_literal_token(token: str) -> bool:
    """Return whether one token is a filename, flag, or placeholder.

    Parameters
    ----------
    token : str
        Token from a header or control label.

    Returns
    -------
    bool
        ``True`` when the token carries literal syntax rather than prose.
    """
    return "{" in token or "." in token or "[" in token or "]" in token or token.startswith("-") or "=" in token


def all_classified_names() -> set[str]:
    """Return every constant and mapping name across both catalogs.

    Returns
    -------
    set[str]
        Catalog names that require a declared capitalization style.
    """
    names: set[str] = set()
    for relative in CATALOGS:
        constants, mappings = catalog_entries(relative)
        names.update(constants)
        names.update(mappings)
    return names


def test_every_catalog_name_is_classified() -> None:
    assert set() == HEADER_CASE & SENTENCE_CASE
    assert all_classified_names() == HEADER_CASE | SENTENCE_CASE


def test_no_mechanical_violations() -> None:
    violations = [
        f"{relative}:{line}: {violation}: {text!r}"
        for relative in CATALOGS
        for line, text in catalog_literals(relative)
        for violation in mechanical_violations(text)
    ]

    assert violations == []


def test_header_case_names_use_header_capitalization() -> None:
    violations: list[str] = []
    for relative in CATALOGS:
        constants, mappings = catalog_entries(relative)
        for name in HEADER_CASE:
            values = [constants[name]] if name in constants else mappings.get(name, [])
            violations.extend(
                f"{relative}:{name}: {violation}: {text!r}"
                for text in values
                for violation in header_case_violations(text)
            )

    assert violations == []


def test_sentence_case_names_use_sentence_capitalization() -> None:
    violations: list[str] = []
    for relative in CATALOGS:
        constants, _mappings = catalog_entries(relative)
        for name in SENTENCE_CASE:
            if name not in constants:
                continue
            violations.extend(
                f"{relative}:{name}: {violation}: {constants[name]!r}"
                for violation in sentence_case_violations(constants[name])
            )

    assert violations == []


def test_ellipsis_only_marks_declared_actions() -> None:
    violations: list[str] = []
    all_constants: dict[str, str] = {}
    for relative in CATALOGS:
        constants, _mappings = catalog_entries(relative)
        all_constants.update(constants)
        for name, text in constants.items():
            if text.endswith(ELLIPSIS) and name not in ELLIPSIS_ACTIONS:
                violations.append(f"{relative}:{name}: undeclared ellipsis: {text!r}")
    for name in ELLIPSIS_ACTIONS:
        if name not in all_constants:
            violations.append(f"{name}: declared action is missing")
        elif not all_constants[name].endswith(ELLIPSIS):
            violations.append(f"{name}: declared action lacks an ellipsis: {all_constants[name]!r}")
        elif name not in HEADER_CASE:
            violations.append(f"{name}: declared action is not header case")

    assert violations == []


def test_mechanical_rule_examples() -> None:
    assert mechanical_violations("It's done.") == [
        "straight apostrophe",
        "trailing period",
    ]
    assert mechanical_violations("Wait...") == ["three-dot ellipsis"]
    assert mechanical_violations("You can change this") == ["first- or second-person pronoun"]
    assert mechanical_violations("Search all notes…") == []


def test_header_rule_examples() -> None:
    assert header_case_violations("New vault") == [
        "lowercase edge word 'vault'",
    ]
    assert header_case_violations("Move To Trash") == ["capitalized short word 'To'"]
    assert header_case_violations("Self-test") == ["lowercase hyphen part 'test'"]
    assert header_case_violations("New Vault") == []
    assert header_case_violations("Move to Trash") == []


def test_sentence_rule_examples() -> None:
    assert sentence_case_violations("lowercase text") == ["sentence does not start uppercase"]
    assert sentence_case_violations("Sentence text") == []
    assert sentence_case_violations("none") == []
    assert sentence_case_violations("{count} notes") == []
    assert sentence_case_violations("1 note") == []
