import reflex as rx
from GitHubActivityDashboard.layout.navbar import NavBar
from GitHubActivityDashboard.state.state import State
from GitHubActivityDashboard.components.loading import LoadingSpinner
from GitHubActivityDashboard.components.card import Card

def dashboard_page() -> rx.Component:
    return rx.box(
        NavBar(),
        rx.container(
            rx.cond(
                State.is_loading_dashboard,
                LoadingSpinner("Učitavanje dashboard podataka..."),
                rx.vstack(
                    rx.heading(f"Dobrodošli, {State.github_username}!", size="8", color="purple"),
                    rx.text("Pregled svih aktivnosti i metrika", size="4", color="purple"),
                    rx.divider(margin_y="2em"),
                    
                    # Metrics Cards
                    rx.heading("📊 Ukupne Metrike", size="7", color="purple"),
                    rx.grid(
                        Card(
                            title="Repozitorijumi",
                            content=f"{State.dashboard_metrics.get('total_repos', 0)} ukupno",
                            icon="📦",
                            badge="Active",
                        ),
                        Card(
                            title="Commits",
                            content=f"{State.dashboard_metrics.get('total_commits', 0)} ukupno",
                            icon="📝",
                            badge="1,847",
                        ),
                        Card(
                            title="Pull Requests",
                            content=f"{State.dashboard_metrics.get('total_prs', 0)} ukupno",
                            icon="🔀",
                            badge="156",
                        ),
                        Card(
                            title="Issues",
                            content=f"{State.dashboard_metrics.get('total_issues', 0)} ukupno",
                            icon="🐛",
                            badge="89",
                        ),
                        columns=rx.breakpoints(initial="1", sm="2", md="4"),
                        spacing="4",
                        width="100%",
                    ),
                    
                    # Activity Summary Box
                    rx.box(
                        rx.vstack(
                            rx.heading("📈 Aktivnost u poslednjih 30 dana", size="6", color="purple"),
                            rx.text("Vaša GitHub aktivnost", color="purple", size="3"),
                            rx.divider(margin_y="1em"),
                            
                            # Custom stat cards
                            rx.hstack(
                                rx.box(
                                    rx.vstack(
                                        rx.text("Activity Score", size="2", color="purple", font_weight="500"),
                                        rx.heading(f"{State.activity_score}%", size="8", color="purple"),
                                        rx.text("Excellent!", size="2", color="green", font_weight="600"),
                                        spacing="2",
                                        align="center",
                                    ),
                                    padding="1.5em",
                                    bg="gray.50",
                                    border_radius="10px",
                                    border="2px solid",
                                    border_color="purple.200",
                                    width="100%",
                                ),
                                rx.box(
                                    rx.vstack(
                                        rx.text("Contributors", size="2", color="purple", font_weight="500"),
                                        rx.heading(State.active_contributors, size="8", color="blue"),
                                        rx.text("Active members", size="2", color="blue", font_weight="600"),
                                        spacing="2",
                                        align="center",
                                    ),
                                    padding="1.5em",
                                    bg="gray.50",
                                    border_radius="10px",
                                    border="2px solid",
                                    border_color="blue.200",
                                    width="100%",
                                ),
                                spacing="4",
                                width="100%",
                            ),
                            
                            # Progress bar
                            rx.box(
                                rx.vstack(
                                    rx.hstack(
                                        rx.text("Overall Progress", size="3", font_weight="600", color="purple"),
                                        rx.text(f"{State.activity_score}%", size="3", color="purple", font_weight="bold"),
                                        width="100%",
                                        justify="between",
                                    ),
                                    rx.progress(
                                        value=State.activity_score,
                                        width="100%",
                                        color_scheme="purple",
                                        height="12px",
                                        border_radius="6px",
                                    ),
                                    spacing="2",
                                ),
                                margin_top="1.5em",
                            ),
                            
                            spacing="4",
                            align="start",
                            width="100%",
                        ),
                        padding="2em",
                        bg="white",
                        border_radius="12px",
                        box_shadow="2",
                        width="100%",
                        margin_top="2em",
                    ),
                    
                    # Quick Actions
                    rx.box(
                        rx.vstack(
                            rx.heading("⚡ Brze akcije", size="6", color="purple"),
                            rx.hstack(
                                rx.link(
                                    rx.button(
                                        rx.hstack(
                                            rx.text("📁"),
                                            rx.text("Vidi sve repos"),
                                            spacing="2",
                                        ),
                                        color_scheme="purple",
                                        _hover={"transform": "scale(1.05)", "transition": "0.2s"},
                                    ),
                                    href="/repos",
                                ),
                                spacing="3",
                                wrap="wrap",
                            ),
                            spacing="3",
                            align="start",
                        ),
                        padding="2em",
                        bg="white",
                        border_radius="12px",
                        box_shadow="2",
                        width="100%",
                        margin_top="2em",
                    ),
                    
                    spacing="6",
                    padding_y="3em",
                ),
            ),
            max_width="1400px",
            padding="2em",
        ),
        min_height="100vh",
        bg="linear-gradient(to bottom, #f7fafc, #edf2f7)",
    )