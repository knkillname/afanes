"""Application controller that owns the shared status and controllers."""

import dataclasses

from afanes.ui.state.browser import BrowserState
from afanes.ui.state.dialogs import PageDialogState
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.navigation import PageNavigator
from afanes.ui.state.pages import PageEditorState
from afanes.ui.state.processing import ProcessingState
from afanes.ui.state.review import ReviewState
from afanes.ui.state.session import VaultSession
from afanes.ui.state.status import UiStatus
from afanes.ui.state.workspace import WorkspaceController


@dataclasses.dataclass(slots=True, eq=False)
class AppState:
    """Single facade exposed to the presentation layer.

    Attributes
    ----------
    status : UiStatus
        Shared message, busy, and session flags.
    workspace : WorkspaceController
        Vault lifecycle and refresh coordination.
    session : VaultSession
        Vault, snapshot, selection, and preview state.
    browser : BrowserState
        Sidebar destination and browser query.
    pages : PageEditorState
        Page draft, editing mode, and conflict state.
    navigation : PageNavigator
        Page movement and history.
    dialogs : PageDialogState
        Pending page dialogs.
    processing : ProcessingState
        Processing Wizard session.
    review : ReviewState
        Guided review session.
    """

    status: UiStatus = dataclasses.field(default_factory=UiStatus)
    _command_lock: CommandLock = dataclasses.field(default_factory=CommandLock, repr=False)
    workspace: WorkspaceController = dataclasses.field(init=False, repr=False)
    session: VaultSession = dataclasses.field(init=False, repr=False)
    browser: BrowserState = dataclasses.field(init=False, repr=False)
    pages: PageEditorState = dataclasses.field(init=False, repr=False)
    navigation: PageNavigator = dataclasses.field(init=False, repr=False)
    dialogs: PageDialogState = dataclasses.field(init=False, repr=False)
    processing: ProcessingState = dataclasses.field(init=False, repr=False)
    review: ReviewState = dataclasses.field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Create the collaborators and wire their shared state."""
        self.session = VaultSession(status=self.status, command_lock=self._command_lock)
        self.browser = BrowserState(session=self.session, command_lock=self._command_lock)
        self.pages = PageEditorState(
            session=self.session,
            status=self.status,
            command_lock=self._command_lock,
        )
        self.navigation = PageNavigator(
            session=self.session,
            pages=self.pages,
            status=self.status,
            command_lock=self._command_lock,
        )
        self.dialogs = PageDialogState(
            session=self.session,
            pages=self.pages,
            navigation=self.navigation,
            status=self.status,
            command_lock=self._command_lock,
        )
        self.processing = ProcessingState(
            session=self.session,
            status=self.status,
            command_lock=self._command_lock,
        )
        self.review = ReviewState(
            session=self.session,
            browser=self.browser,
            processing=self.processing,
            navigation=self.navigation,
            status=self.status,
            command_lock=self._command_lock,
        )
        self.workspace = WorkspaceController(
            session=self.session,
            browser=self.browser,
            pages=self.pages,
            navigation=self.navigation,
            dialogs=self.dialogs,
            processing=self.processing,
            review=self.review,
            status=self.status,
            command_lock=self._command_lock,
        )

    def reset(self) -> None:
        """Return the controller to its initial state.

        Notes
        -----
        Tests call this between cases and the application calls it on
        shutdown. A fresh command lock is created for the next event loop.
        """
        self.dialogs.reset()
        self.pages.reset()
        self.navigation.reset()
        self.processing.reset()
        self.review.reset()
        self.browser.reset()
        self.session.reset()
        self.status.reset()
        self._command_lock.replace()
