import reflex as rx

def ErrorAlert(message: str):
    return rx.alert(
        rx.alert_icon(),
        rx.alert_title("Greška"),
        rx.alert_description(message),
        status="error",
        variant="left_accent",
    )