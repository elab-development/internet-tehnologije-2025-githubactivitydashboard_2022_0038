import reflex as rx

def CustomButton(
    text: str,
    on_click=None,
    color_scheme: str = "blue",
    variant: str = "solid",
    icon: str = "",
    is_loading: bool = False,
    size: str = "3",
):
    return rx.button(
        rx.cond(
            is_loading,
            rx.spinner(size="3"),
            rx.hstack(
                rx.cond(icon != "", rx.text(icon), rx.box()),
                rx.text(text),
                spacing="2",
            ),
        ),
        on_click=on_click,
        color_scheme=color_scheme,
        variant=variant,
        size=size,
        cursor="pointer",
        _hover={"transform": "scale(1.05)", "transition": "0.2s"},
    )