import reflex as rx

def LoadingSpinner(message: str = "Učitavanje..."):
    return rx.center(
        rx.vstack(
            rx.spinner(size="3", color="blue"),
            rx.text(message, size="4", color="purple"),
            spacing="4",
        ),
        min_height="400px",
    )