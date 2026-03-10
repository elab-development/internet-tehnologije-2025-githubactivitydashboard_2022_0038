import reflex as rx
from GitHubActivityDashboard.layout.navbar import NavBar
from GitHubActivityDashboard.state.state import State
from GitHubActivityDashboard.components.github_search import github_search_component
from GitHubActivityDashboard.components.loading import LoadingSpinner


def github_explore_page() -> rx.Component:
    return rx.box(
        NavBar(),
        rx.container(
            rx.vstack(
                # ── Header ──────────────────────────────────────────
                rx.hstack(
                    rx.vstack(
                        rx.heading(
                            "GitHub Explorer",
                            size="8",
                            color="purple",
                        ),
                        rx.text(
                            "Pretražuj GitHub korisnike, pregledaj repozitorijume i sinhroniziraj podatke",
                            size="4",
                            color="gray",
                        ),
                        spacing="2",
                        align="start",
                    ),
                    rx.spacer(),
                    rx.link(
                        rx.button(
                            "← Dashboard",
                            color_scheme="purple",
                            variant="outline",
                        ),
                        href="/dashboard",
                    ),
                    width="100%",
                    align="center",
                ),

                rx.divider(margin_y="1em"),

                # ── Search komponenta ────────────────────────────────
                github_search_component(),

                # ── Sync success poruka ──────────────────────────────
                rx.cond(
                    State.sync_success_message != "",
                    rx.callout(
                        State.sync_success_message,
                        color_scheme="green",
                        size="2",
                    ),
                    rx.box(),
                ),

                spacing="6",
                padding_y="3em",
                align="start",
                width="100%",
            ),
            max_width="900px",
            padding="2em",
        ),
        min_height="100vh",
        bg="linear-gradient(to bottom, #f7fafc, #edf2f7)",
        on_mount=State.check_auth_and_load,
    )