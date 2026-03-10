import reflex as rx
from GitHubActivityDashboard.state.state import State


def github_user_card() -> rx.Component:
    """Prikazuje GitHub profil nakon pretrage"""
    return rx.cond(
        State.github_search_result != {},
        rx.box(
            rx.hstack(
                rx.avatar(
                    src=State.github_search_result.get("avatar_url", ""),
                    size="6",
                    border_radius="full",
                ),
                rx.vstack(
                    rx.heading(
                        State.github_search_result.get("name", ""),
                        size="5",
                        color="purple",
                    ),
                    rx.text(
                        f"@{State.github_search_result.get('login', '')}",
                        size="3",
                        color="gray",
                    ),
                    rx.text(
                        State.github_search_result.get("bio", ""),
                        size="3",
                        color="purple",
                    ),
                    rx.hstack(
                        rx.badge(
                            f"📦 {State.github_search_result.get('public_repos', 0)} repos",
                            color_scheme="purple",
                        ),
                        rx.badge(
                            f"👥 {State.github_search_result.get('followers', 0)} followers",
                            color_scheme="blue",
                        ),
                        rx.badge(
                            f"➡️ {State.github_search_result.get('following', 0)} following",
                            color_scheme="green",
                        ),
                        spacing="2",
                        wrap="wrap",
                    ),
                    rx.link(
                        rx.button(
                            "Otvori na GitHub →",
                            color_scheme="blue",
                            variant="outline",
                            size="2",
                        ),
                        href=State.github_search_result.get("html_url", "#"),
                        is_external=True,
                    ),
                    spacing="2",
                    align="start",
                ),
                spacing="4",
                align="start",
                width="100%",
            ),
            padding="1.5em",
            bg="white",
            border_radius="12px",
            box_shadow="4",
            border="2px solid",
            border_color="purple.200",
            width="100%",
        ),
        rx.box(),
    )


def github_search_component() -> rx.Component:
    """Komponenta za pretragu GitHub korisnika i njihovih repozitorijuma"""
    return rx.box(
        rx.vstack(
            # ── Naslov ──────────────────────────────────────────────
            rx.heading("🔍 Pretraži GitHub", size="6", color="purple"),
            rx.text(
                "Pronađi GitHub korisnika i pregledaj njihove repozitorijume",
                size="3",
                color="gray",
            ),

            # ── Search bar ──────────────────────────────────────────
            rx.hstack(
                rx.input(
                    placeholder="GitHub username (npr. torvalds)",
                    value=State.github_search_query,
                    on_change=State.set_github_search_query,
                    on_key_down=State.handle_search_key,
                    size="3",
                    width="100%",
                    border_color="purple.300",
                    _focus={"border_color": "purple.500"},
                ),
                rx.button(
                    rx.cond(
                        State.is_searching_github,
                        rx.spinner(size="2"),
                        rx.text("Pretraži"),
                    ),
                    on_click=State.search_github_user,
                    color_scheme="purple",
                    size="3",
                    disabled=State.is_searching_github,
                ),
                width="100%",
                spacing="3",
            ),

            # ── Error poruka ────────────────────────────────────────
            rx.cond(
                State.github_search_error != "",
                rx.callout(
                    State.github_search_error,
                    color_scheme="red",
                    size="2",
                ),
                rx.box(),
            ),

            # ── Rezultat — user card ────────────────────────────────
            github_user_card(),

            # ── Repozitorijumi korisnika ────────────────────────────
            rx.cond(
                State.github_search_repos != [],
                rx.vstack(
                    rx.heading(
                        f"📂 Repozitorijumi",
                        size="5",
                        color="purple",
                    ),
                    rx.foreach(
                        State.github_search_repos,
                        lambda repo: rx.box(
                            rx.hstack(
                                rx.vstack(
                                    rx.hstack(
                                        rx.link(
                                            repo["full_name"],
                                            href=repo.get("url", "#"),
                                            is_external=True,
                                            font_weight="bold",
                                            color="purple.600",
                                        ),
                                        rx.cond(
                                            repo.get("private", False),
                                            rx.badge("Private", color_scheme="red", size="1"),
                                            rx.badge("Public", color_scheme="green", size="1"),
                                        ),
                                        spacing="2",
                                    ),
                                    rx.text(
                                        repo.get("description", "Nema opisa"),
                                        size="2",
                                        color="gray",
                                    ),
                                    rx.hstack(
                                        rx.badge(f"⭐ {repo.get('stars', 0)}", color_scheme="yellow"),
                                        rx.badge(f"🍴 {repo.get('forks', 0)}", color_scheme="blue"),
                                        rx.badge(
                                            repo.get("language", "Unknown"),
                                            color_scheme="purple",
                                        ),
                                        rx.text(
                                            f"Ažurirano: {repo.get('updated', '')}",
                                            size="1",
                                            color="gray",
                                        ),
                                        spacing="2",
                                        wrap="wrap",
                                    ),
                                    spacing="1",
                                    align="start",
                                    flex="1",
                                ),
                                rx.button(
                                    "🔄 Sync",
                                    on_click=lambda: State.sync_repo_to_db(
                                        repo.get("owner", ""),
                                        repo.get("name", ""),
                                    ),
                                    color_scheme="green",
                                    variant="outline",
                                    size="2",
                                ),
                                spacing="3",
                                align="center",
                                width="100%",
                            ),
                            padding="1em",
                            bg="white",
                            border_radius="8px",
                            box_shadow="2",
                            width="100%",
                            _hover={"box_shadow": "4", "transform": "translateY(-1px)", "transition": "0.2s"},
                        ),
                    ),
                    spacing="3",
                    width="100%",
                ),
                rx.box(),
            ),

            spacing="4",
            width="100%",
            align="start",
        ),
        padding="1.5em",
        bg="purple.50",
        border_radius="12px",
        width="100%",
    )