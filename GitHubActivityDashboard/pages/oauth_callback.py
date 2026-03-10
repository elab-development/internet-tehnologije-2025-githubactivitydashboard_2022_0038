import reflex as rx
from GitHubActivityDashboard.state.state import State


def oauth_callback_page() -> rx.Component:
    return rx.box(
        rx.center(
            rx.vstack(
                rx.spinner(size="3", color="purple"),
                rx.text("Prijava putem GitHub-a...", color="purple", size="4"),
                spacing="4",
            ),
            height="100vh",
        ),
        on_mount=State.handle_oauth_callback,
    )