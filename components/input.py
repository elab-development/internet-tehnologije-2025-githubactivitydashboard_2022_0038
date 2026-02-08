import reflex as rx

def InputField(
    placeholder: str,
    value: str,
    on_change,
    input_type: str = "text",
    width: str = "100%",
):
    return rx.input(
        placeholder=placeholder,
        value=value,
        on_change=on_change,
        type=input_type,
        width=width,
        color="white",
        padding="0",
        border_radius="0px",
        border="2px solid #e2e8f0",
        font_size="16px",
        _focus={"border_color": "blue.500", "box_shadow": "0 0 0 3px rgba(66, 153, 225, 0.3)"},
    )