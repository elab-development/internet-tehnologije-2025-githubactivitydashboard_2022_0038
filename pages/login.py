import reflex as rx
from GitHubActivityDashboard.components.input import InputField
from GitHubActivityDashboard.state.state import State

def login_page() -> rx.Component:
    return rx.box(
        rx.center(
            rx.vstack(
                rx.heading("🔐 GitHub Activity Dashboard", size="9", color="purple"),
                rx.text("Pratite GitHub aktivnosti u realnom vremenu", size="5", color="purple"),
                rx.divider(margin_y="2em"),
                rx.box(
                    rx.vstack(
                        rx.text("Unesite GitHub korisničko ime:", size="4", font_weight="bold", color="purple"),
                        InputField(
                            placeholder="npr. octocat",
                            value=State.github_username,
                            on_change=State.set_username,
                            width="350px",
                        ),
                        rx.button(
                            rx.hstack(
                                rx.text("🔍"),
                                rx.text("Prijavi se"),
                                spacing="2",
                            ),
                            on_click=State.login,
                            color_scheme="purple",
                            size="3",
                            width="200px",
                        ),
                        spacing="4",
                        align="center",
                    ),
                    padding="3em",
                    bg="white",
                    border_radius="16px",
                    box_shadow="1",
                ),
                spacing="6",
                align="center",
            ),
            min_height="100vh",
        ),
        bg="linear-gradient(to bottom, #f7fafc, #edf2f7)",
    )