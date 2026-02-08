import reflex as rx
from GitHubActivityDashboard.components.button import CustomButton
from GitHubActivityDashboard.state.state import State

def NavBar():
    """Navigation bar with routing links"""
    return rx.box(
        rx.hstack(
            rx.heading("🚀 GitHub Activity Dashboard", size="7", color="purple"),
            rx.spacer(),
            rx.hstack(
                rx.link(
                    rx.button(
                        rx.hstack(
                            rx.text("📊"),
                            rx.text("Dashboard"),
                            spacing="2",
                        ),
                        color_scheme="purple",
                        variant="ghost",
                        _hover={"transform": "scale(1.05)", "transition": "0.2s"},
                    ),
                    href="/dashboard",
                ),
                rx.link(
                    rx.button(
                        rx.hstack(
                            rx.text("📁"),
                            rx.text("Repositories"),
                            spacing="2",
                        ),
                        color_scheme="purple",
                        variant="ghost",
                        _hover={"transform": "scale(1.05)", "transition": "0.2s"},
                    ),
                    href="/repos",
                ),
                CustomButton(
                    "Logout",
                    on_click=State.logout,
                    color_scheme="red",
                    variant="outline",
                    icon="🚪",
                ),
                spacing="2",
            ),
            width="100%",
            padding="1em 2em",
            align="center",
        ),
        bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        width="100%",
        position="sticky",
        top="0",
        z_index="1000",
        box_shadow="3",
    )