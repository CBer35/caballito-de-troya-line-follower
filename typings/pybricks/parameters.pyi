class Port:
    A: Port
    B: Port
    C: Port
    D: Port
    E: Port
    F: Port


class Direction:
    CLOCKWISE: Direction
    COUNTERCLOCKWISE: Direction


class Stop:
    COAST: Stop
    BRAKE: Stop
    HOLD: Stop


class Color:
    BLACK: Color
    BLUE: Color
    GREEN: Color
    YELLOW: Color
    RED: Color
    WHITE: Color
    BROWN: Color
    ORANGE: Color
    PURPLE: Color
    CYAN: Color
    MAGENTA: Color

    def __init__(self, h: int, s: float, v: float) -> None: ...
    @staticmethod
    def hsv(h: int, s: float, v: float) -> Color: ...


class Button:
    LEFT: Button
    CENTER: Button
    RIGHT: Button
    UP: Button
    DOWN: Button
    BLUETOOTH: Button
