from abc import ABC, abstractmethod
from typing import Self

import pygame as pg


class UiElement(ABC):
    def __init__(self, **kwargs: str):
        self.attributes: dict[str, str] = kwargs
        self.children: list[UiElement] = []
        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)
        self.should_draw_self: bool = True
        self.should_draw_children: bool = True

    def add_children(self, *args):
        self.children.extend(args)
        return self

    @abstractmethod
    def build(self, parent_rect: pg.Rect | None = None):
        for child in self.children:
            child.build(self.rect)

        return self

    @abstractmethod
    def draw(self, surface: pg.Surface) -> None:
        if not self.should_draw_children:
            return
        for child in self.children:
            child.draw(surface)


class RectangleElement(UiElement):
    def __init__(self, **kwargs: str):
        super().__init__(**kwargs)
        self.color: pg.Color = pg.Color(0, 0, 0, 0)
        self.border_r: int = -1
        self.border_w: int = 0
        self.border_color: pg.Color = pg.Color(0, 0, 0, 0)
        self.border_top_left_radius: int = -1
        self.border_top_right_radius: int = -1
        self.border_bottom_left_radius: int = -1
        self.border_bottom_right_radius: int = -1
        self.should_draw_self: bool = True
        self.should_draw_children: bool = True

    def build(self, parent_rect: pg.Rect | None = None):
        if parent_rect is None:
            parent_rect = pg.Rect((0, 0), pg.display.get_window_size())
        self.rect.size = resolve_size(self, parent_rect)
        self.rect.topleft = resolve_pos(self, parent_rect)
        self.color = pg.Color(self.attributes.get("color", "#000000"))
        self.border_r: int = size_to_int(
            self.attributes.get("border_radius", "-1px"), self.rect.w
        )
        self.border_w: int = size_to_int(
            self.attributes.get("border_width", "0px"), self.rect.w
        )
        self.border_top_left_radius: int = size_to_int(
            self.attributes.get("border_top_left_radius", "-1px"), self.rect.w
        )
        self.border_top_right_radius: int = size_to_int(
            self.attributes.get("border_top_right_radius", "-1px"), self.rect.w
        )
        self.border_bottom_left_radius: int = size_to_int(
            self.attributes.get("border_bottom_left_radius", "-1px"), self.rect.w
        )
        self.border_bottom_right_radius: int = size_to_int(
            self.attributes.get("border_bottom_right_radius", "-1px"), self.rect.w
        )
        self.border_color: pg.Color = pg.Color(
            self.attributes.get("border_color", "#000000")
        )
        self.should_draw_self = (False if self.attributes.get("draw_self", "True") == "False" else True)
        self.should_draw_children = (False if self.attributes.get("draw_children", "True") == "False" else True)

        return super().build(parent_rect)

    def draw(self, surface: pg.Surface) -> None:
        if not self.should_draw_self:
            return super().draw(surface)

        pg.draw.rect(
            surface,
            self.color,
            self.rect,
            border_radius=self.border_r,
            border_top_left_radius=self.border_top_left_radius,
            border_top_right_radius=self.border_top_right_radius,
            border_bottom_left_radius=self.border_bottom_left_radius,
            border_bottom_right_radius=self.border_bottom_right_radius,
        )

        if self.border_w:
            pg.draw.rect(
                surface,
                self.border_color,
                self.rect,
                width=self.border_w,
                border_radius=self.border_r,
                border_top_left_radius=self.border_top_left_radius,
                border_top_right_radius=self.border_top_right_radius,
                border_bottom_left_radius=self.border_bottom_left_radius,
                border_bottom_right_radius=self.border_bottom_right_radius,
            )

        return super().draw(surface)


class Text(RectangleElement):
    def __init__(
        self,
        text: str = "",
        text_color: str = "#000000",
        font_path: str = pg.font.get_default_font(),
        font_size: str = "32px",
        **kwargs: str
    ):
        super().__init__(**kwargs)
        self.attributes["text"] = text
        self.attributes["text_color"] = text_color
        self.attributes["font_path"] = font_path
        self.attributes["font_size"] = font_size

        self.text: str = text
        self.font: pg.font.Font = pg.font.Font(font_path, size_to_int(font_size, 100))
        self.text_color: pg.Color = pg.Color(text_color)

    def build(self, parent_rect: pg.Rect | None = None):
        if parent_rect is None:
            parent_rect = pg.Rect((0, 0), pg.display.get_window_size())

        self.text: str = self.attributes.get("text", "")
        font_path = self.attributes.get("font_path", pg.font.get_default_font())
        font_size = self.attributes.get("font_size", "32px")
        text_color = self.attributes.get("text_color", "#000000")
        self.font: pg.font.Font = pg.font.Font(
            font_path, size_to_int(font_size, parent_rect.w)
        )
        self.text_color: pg.Color = pg.Color(text_color)

        return super().build(parent_rect)

    def draw(self, surface: pg.Surface) -> None:
        super().draw(surface)
        text_sprite = self.font.render(self.text, True, self.text_color)
        text_rect = text_sprite.get_rect()
        text_rect.center = self.rect.center
        surface.blit(text_sprite, text_rect)


def size_to_int(size_type: str, parent_axis: int) -> int:
    if size_type == "match_parent":
        return parent_axis
    elif size_type[-1] == "%":
        return int(parent_axis * float(size_type[:-1]) / 100)
    elif size_type[-2:] == "px":
        return int(size_type[:-2])

    return 0


def resolve_size(ui_element: UiElement, parent_rect: pg.Rect) -> tuple[int, int]:
    w_type = ui_element.attributes.get("width", "match_parent")

    w: int = size_to_int(w_type, parent_rect.w)

    h_type = ui_element.attributes.get("height", "match_parent")

    h: int = size_to_int(h_type, parent_rect.h)

    return w, h


def resolve_pos(ui_element: UiElement, parent_rect: pg.Rect) -> tuple[int, int]:
    rect = ui_element.rect.copy()

    left_margin: int = size_to_int(
        ui_element.attributes.get("left_margin", "0px"), parent_rect.w
    )
    right_margin: int = size_to_int(
        ui_element.attributes.get("right_margin", "0px"), parent_rect.w
    )

    top_margin: int = size_to_int(
        ui_element.attributes.get("top_margin", "0px"), parent_rect.h
    )
    bottom_margin: int = size_to_int(
        ui_element.attributes.get("bottom_margin", "0px"), parent_rect.h
    )

    rect_with_margin: pg.Rect = pg.Rect(
        0, 0, rect.w + left_margin + right_margin, rect.h + top_margin + bottom_margin
    )

    x_type = ui_element.attributes.get("x", "left")

    if x_type == "left":
        rect_with_margin.left = parent_rect.left
    elif x_type == "right":
        rect_with_margin.right = parent_rect.right
    elif x_type == "center":
        rect_with_margin.centerx = parent_rect.centerx

    rect.x = rect_with_margin.x + left_margin

    y_type = ui_element.attributes.get("y", "top")

    if y_type == "top":
        rect_with_margin.top = parent_rect.top
    elif y_type == "bottom":
        rect_with_margin.bottom = parent_rect.bottom
    elif y_type == "center":
        rect_with_margin.centery = parent_rect.centery

    rect.y = rect_with_margin.y + top_margin

    return rect.topleft
