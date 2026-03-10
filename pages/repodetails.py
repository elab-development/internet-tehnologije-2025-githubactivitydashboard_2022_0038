import reflex as rx
from GitHubActivityDashboard.layout.navbar import NavBar
from GitHubActivityDashboard.state.state import State
from GitHubActivityDashboard.components.loading import LoadingSpinner


def repo_details_page() -> rx.Component:
    return rx.box(
        NavBar(),
        rx.container(
            rx.vstack(
                rx.link(
                    rx.button(
                        "← Nazad na listu",
                        color_scheme="green",
                        variant="outline",
                        _hover={"transform": "scale(1.05)", "transition": "0.2s"},
                    ),
                    href="/repos",
                ),               
                rx.cond(
                    State.is_loading_details,
                    LoadingSpinner("Učitavanje detalja..."),
                    rx.vstack(
                        # Repository header
                        rx.heading(
                            f"📦 {State.repo_full_name}",
                            size="8",
                            color="purple",
                        ),
                        rx.text(
                            State.repo_description,
                            size="4",
                            color="purple",
                        ),
                        
                        # Repository stats
                        rx.hstack(
                            rx.badge(f"⭐ {State.repo_stars} stars", color_scheme="yellow", color="black"),
                            rx.badge(f"🍴 {State.repo_forks} forks", color_scheme="blue", color="black"),
                            rx.badge(f"👁️ {State.repo_watchers} watchers", color_scheme="green", color="black"),
                            rx.badge(f"🐛 {State.repo_open_issues} issues", color_scheme="red", color="black"),
                            spacing="3",
                            wrap="wrap",
                        ),
                        
                        rx.divider(margin_y="2em"),
                        
                        # Filters
                        rx.heading("🎛️ Filteri", size="6", color="purple"),
                        rx.hstack(
                            rx.vstack(
                                rx.text("Vremenski opseg:", font_weight="bold", size="3", color="purple"),
                                rx.select(
                                    ["7", "30", "90"],
                                    value=State.time_range,
                                    on_change=State.set_time_range,
                                    placeholder="Izaberi dane...",
                                ),
                                spacing="2",
                                align="start",
                            ),
                            rx.vstack(
                                rx.text("Tip aktivnosti:", font_weight="bold", size="3", color="purple"),
                                rx.select(
                                    ["all", "commits", "pull_requests", "issues", "releases"],
                                    value=State.activity_type,
                                    on_change=State.set_activity_type,
                                    placeholder="Izaberi tip...",
                                ),
                                spacing="2",
                                align="start",
                            ),
                            spacing="4",
                            wrap="wrap",
                        ),
                        
                        rx.divider(margin_y="2em"),
                        
                        # Activities list
                        rx.heading("📋 Aktivnosti", size="6", color="purple"),
                        rx.cond(
                            State.is_loading_activities,
                            LoadingSpinner("Učitavanje aktivnosti..."),
                            rx.cond(
                                State.activities.length() > 0,
                                rx.vstack(
                                    rx.foreach(
                                        State.activities,
                                        lambda activity: rx.box(
                                            rx.hstack(
                                                rx.text(
                                                    rx.match(
                                                        activity["type"],
                                                        ("commit", "📝"),
                                                        ("pr", "🔀"),
                                                        ("issue", "🐛"),
                                                        ("release", "🎉"),
                                                        "📌",
                                                    ),
                                                    font_size="1.5em",
                                                    color="purple",
                                                ),
                                                rx.vstack(
                                                    rx.text(activity["message"], font_weight="bold", size="4", color="purple"),
                                                    rx.hstack(
                                                        rx.text(f"by {activity['author']}", size="2", color="purple"),
                                                        rx.text(f"• {activity['time']}", size="2", color="purple"),
                                                        spacing="2",
                                                    ),
                                                    spacing="1",
                                                    align="start",
                                                ),
                                                spacing="3",
                                                align="start",
                                                width="100%",
                                            ),
                                            padding="1em",
                                            bg="white",
                                            border_radius="8px",
                                            box_shadow="4",
                                            width="100%",
                                        ),
                                    ),
                                    spacing="3",
                                    width="100%",
                                ),
                                rx.text("Nema aktivnosti za izabrane filtere.", size="4", color="purple"),
                            ),
                        ),
                        
                        spacing="6",
                        align="start",
                        width="100%",
                    ),
                ),
                
                spacing="6",
                padding_y="3em",
                align="start",
            ),
            max_width="1200px",
            padding="2em",
        ),
        min_height="100vh",
        bg="linear-gradient(to bottom, #f7fafc, #edf2f7)",
    )