import reflex as rx
from GitHubActivityDashboard.layout.navbar import NavBar
from GitHubActivityDashboard.state.state import State
from GitHubActivityDashboard.components.loading import LoadingSpinner

def repos_list_page() -> rx.Component:
    def render_repo_card(repo, index):
        """Helper function to render repo card"""
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text("📦", font_size="2em"),
                    rx.badge(repo["language"], color_scheme="blue"),
                    width="100%",
                    justify="between",
                ),
                rx.heading(repo["name"], size="6", color="purple"),
                rx.text(repo["description"], size="3", color="purple", text_align="center"),
                rx.hstack(
                    rx.text(f"⭐ {repo['stars']}", size="2", color="purple"),
                    rx.text(f"🍴 {repo['forks']}", size="2", color="purple"),
                    rx.text(f"🕒 {repo['updated']}", size="2", color="purple"),
                    spacing="3",
                ),
                rx.button(
                    "Vidi detalje",
                    on_click=State.set_selected_repo_index(index),
                    color_scheme="purple",
                    size="4",
                ),
                spacing="3",
                align="center",
            ),
            padding="1.5em",
            border_radius="12px",
            bg="white",
            box_shadow="2",
            _hover={"transform": "translateY(-5px)", "transition": "0.3s"},
        )
    
    return rx.box(
        NavBar(),
        rx.container(
            rx.cond(
                State.is_loading_repos,
                LoadingSpinner("Učitavanje repozitorijuma..."),
                rx.vstack(
                    rx.hstack(
                        rx.heading("📁 GitHub Repozitorijumi", size="8", color="purple"),
                        rx.badge(f"{State.repos_list.length()} repos", color_scheme="purple", font_size="1.2em"),
                        spacing="3",
                        align="center",
                    ),
                    rx.text("Lista svih vaših repozitorijuma", size="4", color="purple"),
                    rx.divider(margin_y="2em"),
                    
                    # Repository cards
                    rx.grid(
                        rx.foreach(
                            State.repos_list,
                            lambda repo: rx.link(
                                rx.box(
                                    rx.vstack(
                                        rx.hstack(
                                            rx.text("📦", font_size="2em"),
                                            rx.badge(repo["language"], color_scheme="blue"),
                                            width="100%",
                                            justify="between",
                                        ),
                                        rx.heading(repo["name"], size="6", color="gray.800"),
                                        rx.text(repo["description"], size="3", color="gray.600", text_align="center"),
                                        rx.hstack(
                                            rx.text(f"⭐ {repo['stars']}", size="2"),
                                            rx.text(f"🍴 {repo['forks']}", size="2"),
                                            rx.text(f"🕒 {repo['updated']}", size="2"),
                                            spacing="3",
                                        ),
                                        spacing="3",
                                        align="center",
                                    ),
                                    padding="1.5em",
                                    border_radius="12px",
                                    bg="white",
                                    box_shadow="lg",
                                    _hover={"transform": "translateY(-5px)", "transition": "0.3s"},
                                ),
                                href=f"/repos/{repo['owner']}/{repo['name']}",  
                            ),
                        ),
                        columns=rx.breakpoints(initial="1", sm="2", md="3"),
                        spacing="4",
                        width="100%",
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