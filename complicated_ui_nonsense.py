import abc
import dataclasses
from typing import Any, Callable, Self, Type

from matplotlib.pylab import f
import pygame as pg


@dataclasses.dataclass
class SpecialFunction:
    input_ids: tuple
    func: Callable
    skip_if_no_input_change: bool=True
    has_no_sideffects: bool=False

    def __call__(self, *args) -> Any:
        return self.func(*args)

@dataclasses.dataclass
class Node:
    val: Any
    func: SpecialFunction
    was_modified: bool=True

@dataclasses.dataclass
class Tree:
    nodes: dict[str, Node]
    outputs: list[SpecialFunction]
    root_ids: list[str]
    skip_ids: set[str]

    @classmethod
    def new(cls, nodes: dict[str, Node], outputs: list[SpecialFunction]):
        root_ids: list[str] = []
        no_side_effect: set[str] = set()
        used_node_ids: set[str] = set()

        for node_id, node in nodes.items():
            if not node.func.input_ids:
                root_ids.append(node_id)

            if node.func.has_no_sideffects:
                no_side_effect.add(node_id)

            for input_id in node.func.input_ids:
                used_node_ids.add(input_id)

        return cls(nodes, outputs, root_ids, no_side_effect.difference(used_node_ids))

    def build_init(self, *, max_no_of_loops: int=10, debug: bool=False, **kwargs: Any): 
        return self.build(max_no_of_loops=max_no_of_loops, debug=debug, init=True, **kwargs)

    def build(self, *, max_no_of_loops: int=10, debug: bool=False, init: bool=False, **kwargs: Any) -> None:
        built_node_ids: list[str] = []

        i = 0

        for root_node_id in self.root_ids:
            root_node = self.nodes[root_node_id]
            new_val = root_node.func()

            if new_val == root_node.val:
                root_node.was_modified = False
            else:
                root_node.val = new_val
                root_node.was_modified = True

            built_node_ids.append(root_node_id)

        for _ in range(0, max_no_of_loops):
            done: bool = True
            for node_id, node in self.nodes.items():
                if node_id in built_node_ids:
                    continue

                if node_id in self.skip_ids:
                    if debug:
                        print(f"SKIPPED {node_id} BECAUSE NO SIDE EFFECT AND NOT USED")
                    continue

                i += 1
                done = False

                for input_id in node.func.input_ids:
                    if input_id not in built_node_ids:
                        continue

                args = []
                can_optimise: bool = node.func.skip_if_no_input_change and not init
                if can_optimise:
                    for input_id in node.func.input_ids:
                        if self.nodes[input_id].was_modified:
                            can_optimise = False
                            break

                    if can_optimise:
                        node.was_modified = False
                        built_node_ids.append(node_id)
                        if debug:
                            print(f"SKIPPED BUILDING {node_id}")
                        continue

                for input_id in node.func.input_ids:
                    if input_id not in built_node_ids:
                        break

                    args.append(self.nodes[input_id].val)
                else: #nobreak
                    new_val = node.func(*args)
                    node.was_modified = new_val != node.val
                    node.val = new_val
                    built_node_ids.append(node_id)
                    if debug:
                        print(f"BUILT {node_id}, NEW_VALUE = {node.val}, INPUTS = {node.func.input_ids}, {args=}")

            if done:
                break

        for output_func in self.outputs:
            args = []
            for node_id in output_func.input_ids:
                args.append(self.nodes[node_id].val)

            output_func(*args)

        if debug: print(f"DEBUG: no. of iterations in ui = {i}\n")

@dataclasses.dataclass
class UIElement(abc.ABC):
    parent_id: str
    id: str

    @classmethod
    @abc.abstractmethod
    def new(cls, parent_id: str, id: str) -> Self:
        return cls(parent_id, id)

    @abc.abstractmethod
    def get_default_nodes(self) -> list[tuple[str, Node]]:
        return []

    @abc.abstractmethod
    def draw(self, screen: pg.surface.Surface) -> None:
        return

    @abc.abstractmethod
    def get_bounding_rect(self) -> pg.Rect:
        return pg.Rect(0, 0, 0, 0)

@dataclasses.dataclass
class UIRect(UIElement):
    parent_id: str
    id: str

    rect: pg.Rect = dataclasses.field(default_factory=lambda : pg.Rect(0, 0, 0, 0))

    @classmethod
    def new(cls, parent_id: str, id: str) -> Self:
        return cls(parent_id, id)

    def get_default_nodes(self) -> list[tuple[str, Node]]:
        nodes = [
            (
                f'{self.id}#left', Node(self.rect.x, SpecialFunction((), lambda: self.rect.x, has_no_sideffects=True)),
            ),
            (
                f'{self.id}#top', Node(self.rect.right, SpecialFunction((), lambda: self.rect.top, has_no_sideffects=True)),
            ),
            (
                f'{self.id}#width', Node(self.rect.top, SpecialFunction((), lambda: self.rect.w, has_no_sideffects=True)),
            ),
            (
                f'{self.id}#height', Node(self.rect.bottom, SpecialFunction((), lambda: self.rect.h, has_no_sideffects=True)),
            ),
        ]

        return nodes

    def draw(self, screen: pg.Surface) -> None:
        pg.draw.rect(screen, (200, 200, 200), self.rect)
        pg.draw.rect(screen, (200, 0, 0), self.rect, 10)

    def get_bounding_rect(self) -> pg.Rect:
        return self.rect

def rect_x_align(token: str, ui_element: UIElement) -> SpecialFunction:
    assert isinstance(ui_element, UIRect)
    if token == 'left':
        def left_align(left):
            ui_element.rect.left = left
            return left
        return SpecialFunction((ui_element.parent_id+"#left",), left_align)

    if token == 'right':
        def right_align(left, width):
            ui_element.rect.right = left + width
            return ui_element.rect.right
        return SpecialFunction((ui_element.parent_id+"#left", ui_element.parent_id+"#width"), right_align)

    raise ValueError("Unknown \"x-align\" value, \"{token}\"")

def rect_y_align(token: str, ui_element: UIElement) -> SpecialFunction:
    assert isinstance(ui_element, UIRect)
    if token == 'top':
        def top_align(top):
            ui_element.rect.top = top
            return top
        return SpecialFunction((ui_element.parent_id+"#top",), top_align)

    if token == 'bottom':
        def bottom_align(top, height):
            ui_element.rect.bottom = top+height
            return ui_element.rect.bottom
        return SpecialFunction((ui_element.parent_id+"#top", ui_element.parent_id+"#height"), bottom_align)

    raise ValueError("Unknown \"x-align\" value, \"{token}\"")

def rect_width(token: str, ui_element: UIElement) -> SpecialFunction:
    assert isinstance(ui_element, UIRect)
    percent = int(token)
    def w(parent_w):
        ui_element.rect.w = parent_w * percent / 100
        return ui_element.rect.w

    return SpecialFunction(
        (f'{ui_element.parent_id}#width', ),
        w
    )

def rect_height(token: str, ui_element: UIElement) -> SpecialFunction:
    assert isinstance(ui_element, UIRect)
    percent = int(token)
    def h(parent_h):
        ui_element.rect.height = parent_h * percent / 100
        return ui_element.rect.height

    return SpecialFunction(
        (f'{ui_element.parent_id}#height', ),
        h
    )

constructors: dict[Type[UIElement], dict[str, Callable[[str, UIElement], SpecialFunction]]] = {
    UIRect: {
        'x-align': rect_x_align,
        'y-align': rect_y_align,
        'width': rect_width,
        'height': rect_height,
    }
}

SPECIAL_CHARS: str = "{};:"

def ui_element_token_to_type(token: str) -> Type[UIElement]:
    if token == 'Rect':
        return UIRect

    raise ValueError(f"Unknown UI Element \"{token}\".")

@dataclasses.dataclass
class UI:
    vals: Tree
    ui_elements: list[UIElement]

    @classmethod
    def init(cls, definition: str, left: Callable[[], int], top: Callable[[], int], width: Callable[[], int], height: Callable[[], int]) -> Self:
        tokens: list[str] = []
        last_token: str = ''

        for char in definition:
            if char.isspace():
                if last_token: tokens.append(last_token)
                last_token = ''
                continue

            if char in SPECIAL_CHARS:
                if last_token: tokens.append(last_token)
                last_token = char
                continue

            last_token = last_token + char

        current_ui_heirarchy: list[str] = []
        id_counter = 0

        i = 0
        no_of_tokens = len(tokens)

        ui_elements: list[UIElement] = []
        nodes: dict[str, Node] = {
            '#left': Node(0, SpecialFunction((), left, skip_if_no_input_change=False)),
            '#top': Node(0, SpecialFunction((), top, skip_if_no_input_change=False)),
            '#width': Node(0, SpecialFunction((), width, skip_if_no_input_change=False)),
            '#height': Node(0, SpecialFunction((), height, skip_if_no_input_change=False)),
        }

        while i < no_of_tokens:
            token = tokens[i]

            if token == '{':
                try:
                    token = tokens[i-1]
                except IndexError:
                    raise ValueError("Missing token before \"{\"")
                id_counter += 1

                ui_element_id: str = token + f'{id_counter}'

                parent_id = current_ui_heirarchy[-1] if current_ui_heirarchy else ''
                current_ui_heirarchy.append(ui_element_id)

                ui_element = ui_element_token_to_type(token).new(parent_id, ui_element_id)

                ui_elements.append(ui_element)

                for node_id, node in ui_element.get_default_nodes():
                    nodes[node_id] = node

                i += 1
                continue

            if token == '}':
                if not current_ui_heirarchy:
                    raise ValueError("Too many '}'")

                current_ui_heirarchy.pop()

                i += 1
                continue

            if token == ':':
                if not ui_elements:
                    raise ValueError("\":\" found outside of any ui element")

                attribute = tokens[i-1]
                value = tokens[i+1]

                ui_element_id = current_ui_heirarchy[-1]
                ui_element = ui_elements[0]
                for element in ui_elements:
                    if element.id != ui_element_id:
                        continue

                    ui_element = element
                    break

                new_node: Node = Node(None, constructors[type(ui_element)][attribute](value, ui_element))
                nodes[f"{ui_element.id}#{attribute}"] = new_node

            i += 1

        return cls(Tree.new(nodes, []), ui_elements)

    def build_init(self, max_no_of_loops: int = 10, debug: bool = False,) -> None:
        self.vals.build_init(max_no_of_loops=max_no_of_loops, debug=debug)

    def build(self, max_no_of_loops: int = 10, debug: bool = False,) -> None:
        self.vals.build(max_no_of_loops=max_no_of_loops, debug=debug)

    def draw(self, screen: pg.surface.Surface) -> None:
        for ui_element in self.ui_elements:
            ui_element.draw(screen)

# x = 5
# 
# t = Tree(
#     {
#         '#in1': Node(0, SpecialFunction((), lambda : x)),
#         'mid1': Node('', SpecialFunction(('#in1', ), lambda in1: str(in1))),
#         'mid2': Node('', SpecialFunction(('#in1', ), lambda in1: in1+5)),
#         'out1': Node('', SpecialFunction(('mid1', 'mid2'), lambda mid1, mid2: mid1 + str(mid2)))
#     },
#     (SpecialFunction(('out1',), lambda out1: print(out1)), )
# )
# 
# t.build()
# 
# for name, node in t.nodes.items():
#     print(f"{name}: {node.val}")
# 
# x = 7
# 
# t.build()
# 
# for name, node in t.nodes.items():
#     print(f"{name}: {node.val}")

INPUT = \
"""
Rect {
    x-align: left;
    y-align: top;

    Rect {
       x-align: right;
       y-align: bottom;
       width: 50;
       height: 50;
    }

    width: 75;
    height: 100;
}
"""
pg.init()

screen = pg.display.set_mode((500, 500), flags=pg.RESIZABLE)


ui = UI.init(INPUT, lambda : 0, lambda : 0, lambda : pg.display.get_window_size()[0], lambda : pg.display.get_window_size()[1])

ui.build_init(debug=True)

for ui_element in ui.ui_elements:
    print(ui_element.id)
    bounding_rect = ui_element.get_bounding_rect()

    print(f"{bounding_rect = }")
    print()

is_running = True

debug = True

while is_running:
    screen.fill((0, 0, 0))

    for event in pg.event.get():
        if event.type == pg.QUIT:
            is_running = False

    ui.build(debug=debug)
    debug = False
    ui.draw(screen)
    pg.display.update()
