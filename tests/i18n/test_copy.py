"""Copy gate for the English source messages and the Spanish catalogs.

The gate validates the English source modules, the reviewed Spanish ``.po``
files, and their compiled ``.mo`` counterparts. Mechanical rules apply to every
message; capitalization rules apply to the declared English classification sets
and to Spanish sentence-style capitalization. The gate has no baseline: every
violation must be fixed, never recorded.
"""

import ast
import gettext
import re
import string
from pathlib import Path

import afanes.core.errors
import afanes.i18n.po

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "afanes"
UI_SOURCE = SOURCE_ROOT / "i18n" / "ui" / "en.py"
CLI_SOURCE = SOURCE_ROOT / "i18n" / "cli" / "en.py"
MESSAGES_SOURCE = SOURCE_ROOT / "i18n" / "messages" / "en.py"
TEMPLATES_SOURCE = SOURCE_ROOT / "i18n" / "templates" / "en.py"
LOCALES_ROOT = SOURCE_ROOT / "i18n" / "locales"
ELLIPSIS = "…"
STRAIGHT_APOSTROPHE = "'"
THREE_DOTS = "..."
TRAILING_PERIOD = re.compile(r"\.\s*$")
WORD_CHARACTERS = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")
TRIM_CHARACTERS = ".,;:!?()[]“”«»\"'"
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
ENGLISH_PRONOUNS = re.compile(r"\b(?:I|me|my|mine|we|us|our|ours|you|your|yours)\b", re.IGNORECASE)
SPANISH_PRONOUNS = re.compile(
    r"\b(?:yo|me|mí|mis|mío|mía|míos|mías|nosotros|nosotras|nos|nuestro|nuestra|nuestros|nuestras|"
    r"tú|te|ti|tu|tus|tuyo|tuya|tuyos|tuyas|usted|ustedes|vosotros|vosotras|os|vuestro|vuestra|"
    r"vuestros|vuestras)\b",
    re.IGNORECASE,
)
SPANISH_ALLOWED_CAPITALS = frozenset(
    {
        "Afanes",
        "English",
        "Español",
        "Flet",
        "Markdown",
        "GNU",
        "Affero",
        "General",
        "Public",
        "License",
        "SDK",
        "JSON",
        "YAML",
        "DIR",
        "YYYY",
        "MM",
        "DD",
        "Fecha",
        "Más",
        "Nombre",
        "Referencia",
        "AM",
        "PM",
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
        "LANGUAGE_ENGLISH",
        "LANGUAGE_MENU",
        "LANGUAGE_MENU_TITLE",
        "LANGUAGE_SPANISH",
        "LANGUAGE_SYSTEM",
        "LOG_CARD_EMPTY",
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
        "HELP_OPTION",
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
        "LANGUAGE_RESTART",
        "LOG_CARD_DESCRIPTION_EMPTY",
        "LOG_CARD_LABEL",
        "LOG_DAY_TOOLTIP_MANY",
        "LOG_DAY_TOOLTIP_NONE",
        "LOG_DAY_TOOLTIP_ONE",
        "LOG_EMPTY",
        "LOG_MODE_NOT_REMEMBERED",
        "LOG_MONTH_ENTRY_MARK",
        "LOG_NEW_MONTH_ENTRY",
        "LOG_NEW_YEAR_ENTRY",
        "LOG_OPEN_MONTH_ENTRY",
        "LOG_OPEN_YEAR_ENTRY",
        "LOG_PLACEHOLDER",
        "LOG_WRITE_FAILED",
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
        "NOTE_WORD_MANY",
        "NOTE_WORD_ONE",
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
        "PREFERENCES_CORRUPT",
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
        "PROCESSING_PLAN_STEP",
        "PROCESSING_PLAN_FAILED",
        "PROCESSING_DESTINATION_TRASH",
        "PROCESSING_PLAN_OWNER",
        "PROCESSING_PLAN_SCAFFOLD",
        "PROCESSING_PROJECT_HINT",
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
        "REFERENCE_COUNT",
        "REFERENCE_WORD_MANY",
        "REFERENCE_WORD_ONE",
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
        "USAGE_ERROR",
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
        "LANGUAGE_MENU",
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

DOMAINS = {
    "afanes-ui": (UI_SOURCE, LOCALES_ROOT / "es" / "LC_MESSAGES" / "afanes-ui.po"),
    "afanes-cli": (CLI_SOURCE, LOCALES_ROOT / "es" / "LC_MESSAGES" / "afanes-cli.po"),
    "afanes-messages": (MESSAGES_SOURCE, LOCALES_ROOT / "es" / "LC_MESSAGES" / "afanes-messages.po"),
}


def catalog_entries(path: Path) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Return string constants and mapping entries of one English module.

    Parameters
    ----------
    path : pathlib.Path
        English source module.

    Returns
    -------
    tuple[dict[str, str], dict[str, dict[str, str]]]
        Constant name to value, and mapping name to key-value pairs.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    constants: dict[str, str] = {}
    mappings: dict[str, dict[str, str]] = {}
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
            pairs: dict[str, str] = {}
            for key_node, value_node in zip(value.args[0].keys, value.args[0].values, strict=True):
                if (
                    isinstance(key_node, ast.Constant)
                    and isinstance(key_node.value, str)
                    and isinstance(value_node, ast.Constant)
                    and isinstance(value_node.value, str)
                ):
                    pairs[key_node.value] = value_node.value
            mappings[name] = pairs
    return constants, mappings


def message_templates(path: Path) -> dict[str, str]:
    """Return the English message templates keyed by message code value.

    Parameters
    ----------
    path : pathlib.Path
        English message module.

    Returns
    -------
    dict[str, str]
        Message code value to English template.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    templates: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            value_node_root = node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            value_node_root = node.value
        else:
            continue
        if name != "TEMPLATES" or not isinstance(value_node_root, ast.Dict):
            continue
        for key_node, value_node in zip(value_node_root.keys, value_node_root.values, strict=True):
            if (
                isinstance(key_node, ast.Attribute)
                and isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, str)
            ):
                code = afanes.core.errors.MessageCode[key_node.attr]
                templates[code.value] = value_node.value
    return templates


def catalog_literals(path: Path) -> list[tuple[int, str]]:
    """Return every string literal in one module except docstrings.

    Parameters
    ----------
    path : pathlib.Path
        Python module to scan.

    Returns
    -------
    list[tuple[int, str]]
        Line number and literal value.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
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


def expected_entries() -> dict[str, dict[str, str]]:
    """Return the expected Spanish contexts and English msgids per domain.

    Returns
    -------
    dict[str, dict[str, str]]
        Domain to context-to-English-message mapping.
    """
    ui_constants, ui_mappings = catalog_entries(UI_SOURCE)
    cli_constants, _cli_mappings = catalog_entries(CLI_SOURCE)
    expected: dict[str, dict[str, str]] = {"afanes-ui": dict(ui_constants), "afanes-cli": dict(cli_constants)}
    for mapping_name, pairs in ui_mappings.items():
        for key, value in pairs.items():
            expected["afanes-ui"][f"{mapping_name}.{key}"] = value
    expected["afanes-messages"] = message_templates(MESSAGES_SOURCE)
    template_constants, _template_mappings = catalog_entries(TEMPLATES_SOURCE)
    expected["afanes-messages"].update(template_constants)
    return expected


def actual_entries(path: Path) -> dict[str, tuple[str, str]]:
    """Return the contexts and messages of one Spanish catalog.

    Parameters
    ----------
    path : pathlib.Path
        Spanish ``.po`` file.

    Returns
    -------
    dict[str, tuple[str, str]]
        Context to msgid and msgstr pair.
    """
    catalog = afanes.i18n.po.PoCatalog.from_path(path)
    return {entry.context: (entry.msgid, entry.msgstr) for entry in catalog.messages if entry.context is not None}


def parity_violations(expected: dict[str, str], actual: dict[str, tuple[str, str]], domain: str) -> list[str]:
    """Return missing, extra, mismatched, or blank catalog entries.

    Parameters
    ----------
    expected : dict[str, str]
        Context to English source message.
    actual : dict[str, tuple[str, str]]
        Context to msgid and msgstr pair.
    domain : str
        Gettext domain used in failure messages.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the catalogs agree.
    """
    violations: list[str] = []
    violations.extend(f"{domain}: missing context {context!r}" for context in sorted(set(expected) - set(actual)))
    violations.extend(f"{domain}: extra context {context!r}" for context in sorted(set(actual) - set(expected)))
    for context in sorted(set(expected) & set(actual)):
        msgid, msgstr = actual[context]
        if msgid != expected[context]:
            violations.append(f"{domain}:{context}: msgid {msgid!r} does not match source {expected[context]!r}")
        if not msgstr.strip():
            violations.append(f"{domain}:{context}: blank msgstr")
    return violations


def placeholders(text: str) -> list[str]:
    """Return the interpolation field names of one template.

    Parameters
    ----------
    text : str
        Message template.

    Returns
    -------
    list[str]
        Field names in source order.
    """
    return [name for _, name, _, _ in string.Formatter().parse(text) if name is not None]


def placeholder_violations(expected: dict[str, str], actual: dict[str, tuple[str, str]], domain: str) -> list[str]:
    """Return placeholder mismatches between English and Spanish.

    Parameters
    ----------
    expected : dict[str, str]
        Context to English source message.
    actual : dict[str, tuple[str, str]]
        Context to msgid and msgstr pair.
    domain : str
        Gettext domain used in failure messages.

    Returns
    -------
    list[str]
        Violation descriptions, empty when every placeholder matches.
    """
    violations: list[str] = []
    for context in sorted(set(expected) & set(actual)):
        _msgid, msgstr = actual[context]
        if sorted(placeholders(expected[context])) != sorted(placeholders(msgstr)):
            violations.append(
                f"{domain}:{context}: placeholders {placeholders(expected[context])} != {placeholders(msgstr)}"
            )
    return violations


def mechanical_violations(text: str, language: str) -> list[str]:
    """Return mechanical writing-style violations for one string.

    Parameters
    ----------
    text : str
        Copy string to inspect.
    language : str
        Language of the string, either ``en`` or ``es``.

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
    pronouns = SPANISH_PRONOUNS if language == "es" else ENGLISH_PRONOUNS
    if pronouns.search(text):
        violations.append("first- or second-person pronoun")
    return violations


def header_case_violations(text: str) -> list[str]:
    """Return the header-capitalization violations in one English string.

    Parameters
    ----------
    text : str
        Header or short control label to inspect.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the string conforms.
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
    """Return the sentence-capitalization violations in one English string.

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
    first_token = stripped.split()[0]
    if is_literal_token(first_token):
        return []
    if " " not in stripped and stripped.islower():
        return []
    if stripped[0].isupper():
        return []
    return ["sentence does not start uppercase"]


def spanish_case_violations(text: str) -> list[str]:
    """Return the Spanish sentence-style capitalization violations.

    Parameters
    ----------
    text : str
        Spanish message to inspect.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the string follows Spanish
        sentence-style capitalization.
    """
    stripped = text.strip()
    if not stripped or not WORD_CHARACTERS.search(stripped):
        return []
    if stripped[0] in "{0123456789":
        return []
    if " " not in stripped and stripped.islower():
        return []
    violations: list[str] = []
    for segment in re.split(r"(?<=[.!?])\s+|\n+", stripped):
        words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ-]*", segment)
        if not words:
            continue
        if segment.lstrip()[0] in "{0123456789":
            continue
        first_token = segment.lstrip().split()[0]
        if is_literal_token(first_token):
            continue
        if words[0][0].islower() and len(words) > 1:
            violations.append(f"sentence does not start uppercase: {segment!r}")
        violations.extend(
            f"unexpected title-case word {word!r}"
            for word in words[1:]
            if word[0].isupper() and not word.isupper() and word not in SPANISH_ALLOWED_CAPITALS
        )
    return violations


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
    """Return every English constant and mapping name across both surfaces.

    Returns
    -------
    set[str]
        Catalog names that require a declared capitalization style.
    """
    names: set[str] = set()
    for source in (UI_SOURCE, CLI_SOURCE):
        constants, mappings = catalog_entries(source)
        names.update(constants)
        names.update(mappings)
    return names


def all_spanish_catalogs() -> tuple[Path, ...]:
    """Return every reviewed Spanish source catalog.

    Returns
    -------
    tuple[pathlib.Path, ...]
        ``.po`` files in source order.
    """
    return tuple(sorted(LOCALES_ROOT.rglob("*.po")))


def test_every_catalog_name_is_classified() -> None:
    assert set() == HEADER_CASE & SENTENCE_CASE
    assert all_classified_names() == HEADER_CASE | SENTENCE_CASE


def test_every_english_message_has_a_spanish_entry() -> None:
    expected = expected_entries()
    violations: list[str] = []
    for domain, (_source, path) in DOMAINS.items():
        violations.extend(parity_violations(expected[domain], actual_entries(path), domain))

    assert violations == []


def test_spanish_placeholders_match_english() -> None:
    expected = expected_entries()
    violations: list[str] = []
    for domain, (_source, path) in DOMAINS.items():
        violations.extend(placeholder_violations(expected[domain], actual_entries(path), domain))

    assert violations == []


def test_english_sources_follow_the_mechanical_rules() -> None:
    violations = [
        f"{path.name}:{line}: {violation}: {text!r}"
        for path in (UI_SOURCE, CLI_SOURCE, MESSAGES_SOURCE, TEMPLATES_SOURCE)
        for line, text in catalog_literals(path)
        for violation in mechanical_violations(text, "en")
    ]

    assert violations == []


def test_spanish_catalogs_follow_the_mechanical_rules() -> None:
    violations: list[str] = []
    for path in all_spanish_catalogs():
        catalog = afanes.i18n.po.PoCatalog.from_path(path)
        for entry in catalog.messages:
            violations.extend(
                f"{path.name}:{entry.context}: {violation}: {entry.msgstr!r}"
                for violation in mechanical_violations(entry.msgstr, "es")
            )

    assert violations == []


def test_english_header_case_holds() -> None:
    constants, mappings = catalog_entries(UI_SOURCE)
    cli_constants, _cli_mappings = catalog_entries(CLI_SOURCE)
    constants.update(cli_constants)
    violations: list[str] = []
    for name in HEADER_CASE:
        values = [constants[name]] if name in constants else list(mappings.get(name, {}).values())
        violations.extend(
            f"{name}: {violation}: {text!r}" for text in values for violation in header_case_violations(text)
        )

    assert violations == []


def test_english_sentence_case_holds() -> None:
    constants, _mappings = catalog_entries(UI_SOURCE)
    cli_constants, _cli_mappings = catalog_entries(CLI_SOURCE)
    constants.update(cli_constants)
    violations = [
        f"{name}: {violation}: {constants[name]!r}"
        for name in SENTENCE_CASE
        if name in constants
        for violation in sentence_case_violations(constants[name])
    ]

    assert violations == []


def test_message_templates_use_sentence_capitalization() -> None:
    violations = [
        f"{code}: {violation}: {text!r}"
        for code, text in message_templates(MESSAGES_SOURCE).items()
        for violation in sentence_case_violations(text)
    ]

    assert violations == []


def test_template_labels_use_the_expected_capitalization() -> None:
    constants, _mappings = catalog_entries(TEMPLATES_SOURCE)
    violations: list[str] = []
    for name, text in constants.items():
        found = header_case_violations(text) if name.endswith("_LABEL") else sentence_case_violations(text)
        violations.extend(f"{name}: {violation}: {text!r}" for violation in found)

    assert violations == []


def test_spanish_catalogs_use_sentence_style_capitalization() -> None:
    violations: list[str] = []
    for path in all_spanish_catalogs():
        catalog = afanes.i18n.po.PoCatalog.from_path(path)
        violations.extend(
            f"{path.name}:{entry.context}: {violation}: {entry.msgstr!r}"
            for entry in catalog.messages
            for violation in spanish_case_violations(entry.msgstr)
        )

    assert violations == []


def test_ellipsis_marks_only_further_input_actions() -> None:
    constants, _mappings = catalog_entries(UI_SOURCE)
    cli_constants, _cli_mappings = catalog_entries(CLI_SOURCE)
    constants.update(cli_constants)
    violations: list[str] = []
    for name, text in constants.items():
        if text.endswith(ELLIPSIS) and name not in ELLIPSIS_ACTIONS:
            violations.append(f"{name}: undeclared ellipsis: {text!r}")
    for name in ELLIPSIS_ACTIONS:
        if name not in constants:
            violations.append(f"{name}: declared action is missing")
        elif not constants[name].endswith(ELLIPSIS):
            violations.append(f"{name}: declared action lacks an ellipsis")
        elif name not in HEADER_CASE:
            violations.append(f"{name}: declared action is not header case")

    assert violations == []


def test_spanish_ellipsis_follows_the_english_action_set() -> None:
    path = DOMAINS["afanes-ui"][1]
    catalog = afanes.i18n.po.PoCatalog.from_path(path)
    violations: list[str] = []
    for entry in catalog.messages:
        if entry.context in ELLIPSIS_ACTIONS:
            if not entry.msgstr.endswith(ELLIPSIS):
                violations.append(f"{entry.context}: action lacks an ellipsis")
        elif entry.msgstr.endswith(ELLIPSIS):
            violations.append(f"{entry.context}: undeclared ellipsis")

    assert violations == []


def test_compiled_catalogs_are_current() -> None:
    violations: list[str] = []
    for path in all_spanish_catalogs():
        catalog = afanes.i18n.po.PoCatalog.from_path(path)
        compiled = path.with_suffix(".mo")
        if not compiled.is_file():
            violations.append(f"{compiled.name}: missing compiled catalog")
        elif compiled.read_bytes() != catalog.to_mo():
            violations.append(f"{compiled.name}: compiled catalog is stale")

    assert violations == []


def test_compiled_catalogs_load_and_match_their_sources() -> None:
    violations: list[str] = []
    for path in all_spanish_catalogs():
        catalog = afanes.i18n.po.PoCatalog.from_path(path)
        compiled = path.with_suffix(".mo")
        if not compiled.is_file():
            violations.append(f"{compiled.name}: missing compiled catalog")
            continue
        with compiled.open("rb") as stream:
            translations = gettext.GNUTranslations(stream)
        for entry in catalog.messages:
            if entry.context is None:
                continue
            if translations.pgettext(entry.context, entry.msgid) != entry.msgstr:
                violations.append(f"{compiled.name}:{entry.context}: compiled value does not match source")

    assert violations == []


def test_the_gate_offers_no_exception_ledger() -> None:
    assert "BASELINE" not in globals()
    assert "ALLOWED_VIOLATIONS" not in globals()


def test_ui_modules_do_not_read_a_copy_module_directly() -> None:
    offenders = [
        path.relative_to(SOURCE_ROOT).as_posix()
        for path in sorted((SOURCE_ROOT / "ui").rglob("*.py"))
        if "afanes.ui.strings" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_a_missing_entry_is_reported() -> None:
    violations = parity_violations({"GREETING": "Hello"}, {}, "test")

    assert violations == ["test: missing context 'GREETING'"]


def test_an_extra_entry_is_reported() -> None:
    violations = parity_violations({}, {"GREETING": ("Hello", "Hola")}, "test")

    assert violations == ["test: extra context 'GREETING'"]


def test_a_context_mismatch_is_reported() -> None:
    violations = parity_violations({"GREETING": "Hello"}, {"FAREWELL": ("Hello", "Adiós")}, "test")

    assert "test: missing context 'GREETING'" in violations
    assert "test: extra context 'FAREWELL'" in violations


def test_a_msgid_mismatch_is_reported() -> None:
    violations = parity_violations({"GREETING": "Hello"}, {"GREETING": ("Hi", "Hola")}, "test")

    assert violations == ["test:GREETING: msgid 'Hi' does not match source 'Hello'"]


def test_a_blank_translation_is_reported() -> None:
    violations = parity_violations({"GREETING": "Hello"}, {"GREETING": ("Hello", "  ")}, "test")

    assert violations == ["test:GREETING: blank msgstr"]


def test_a_placeholder_mismatch_is_reported() -> None:
    violations = placeholder_violations(
        {"WELCOME": "Welcome {name}"},
        {"WELCOME": ("Welcome {name}", "Bienvenido {title}")},
        "test",
    )

    assert violations == ["test:WELCOME: placeholders ['name'] != ['title']"]


def test_a_straight_apostrophe_is_reported() -> None:
    assert mechanical_violations("It's done", "en") == ["straight apostrophe"]


def test_a_three_dot_ellipsis_is_reported() -> None:
    assert mechanical_violations("Wait...", "en") == ["three-dot ellipsis"]


def test_a_trailing_period_is_reported() -> None:
    assert mechanical_violations("Done.", "en") == ["trailing period"]


def test_a_spanish_pronoun_is_reported() -> None:
    assert mechanical_violations("Tú puedes cambiar esto", "es") == ["first- or second-person pronoun"]


def test_an_english_header_case_violation_is_reported() -> None:
    assert header_case_violations("New vault") == ["lowercase edge word 'vault'"]


def test_a_spanish_title_case_violation_is_reported() -> None:
    assert spanish_case_violations("Nueva Bóveda") == ["unexpected title-case word 'Bóveda'"]


def test_spanish_sentence_case_is_accepted() -> None:
    assert spanish_case_violations("Nueva bóveda") == []
    assert spanish_case_violations("Vacía - categoría general, sin cuerpo inicial") == []
    assert spanish_case_violations("{count} notas") == []
    assert spanish_case_violations("ninguna") == []


def test_a_stale_compiled_catalog_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "sample.po"
    path.write_text(
        'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        'msgctxt "GREETING"\nmsgid "Hello"\nmsgstr "Hola"\n',
        encoding="utf-8",
    )
    path.with_suffix(".mo").write_bytes(b"stale")
    catalog = afanes.i18n.po.PoCatalog.from_path(path)

    assert path.with_suffix(".mo").read_bytes() != catalog.to_mo()
