import reflex as rx

def Card(
    title: str,
    content: str,
    icon: str = "📊",
    on_click=None,
    badge: str = "",
    children=None,
):
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(icon, font_size="2.5em", color="purple"),
                rx.cond(
                    badge != "",
                    rx.badge(badge, color_scheme="green"),
                    rx.box(),
                ),
                width="100%",
                justify="between",
            ),
            rx.heading(title, size="6", color="purple"),
            rx.text(content, size="3", color="purple", text_align="center"),
            rx.cond(
                children is not None,
                children,
                rx.box(),
            ),
            spacing="3",
            align="center",
        ),
        padding="1.5em",
        border_radius="12px",
        bg="white",
        box_shadow="2",
        cursor="pointer" if on_click else "default",
        on_click=on_click,
        _hover={"transform": "translateY(-5px)", "transition": "0.3s"} if on_click else {},
        width="100%",
    )