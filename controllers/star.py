import asyncio

from flet import (
    ElevatedButton,
    Stack,
    Column,
    Text,
    ResponsiveRow,
    canvas,
    Paint,
    PaintingStyle,
    DataTable,
    DataColumn,
    DataRow,
    DataCell,
    Divider,
    Dropdown,
    dropdown,
    ButtonStyle,
    MaterialState,
    BorderSide,
    TextField,
)
from utils.locale import loc

from models.constants import files_cache
from models.interface import Controller, ScrollingFrame
from models.trove.star_chart import get_star_chart, StarType


class RoundButton(ElevatedButton):
    def __init__(self, size=20, bgcolor="blue", **kwargs):
        super().__init__(width=size, height=size, bgcolor=bgcolor, **kwargs)


class StarChartController(Controller):
    def setup_controls(self):
        if not hasattr(self, "map"):
            self.selected_stat = None
            self.star_chart = get_star_chart(files_cache["star_chart.json"])
            self.map = ResponsiveRow()
            self.star_details = Column(col={"xxl": 6.5})
            if self.page.params:
                _id = self.page.params.get("id", None)
                self.page.params.clear()
                if _id:
                    asyncio.create_task(self.start_with_build_id(_id))
                    return
        self.map.controls.clear()
        self.star_buttons = Stack(
            controls=[
                Text(
                    f"{self.star_chart.activated_stars_count}/{self.star_chart.max_nodes}",
                    size=40,
                    left=30,
                ),
                ElevatedButton(
                    loc("Reset"), top=50, left=40, on_click=self.reset_chart
                ),
                *[
                    RoundButton(
                        style=ButtonStyle(
                            side={
                                MaterialState.DEFAULT: (
                                    BorderSide(3, "yellow")
                                    if self.selected_stat
                                    in [stat["name"] for stat in star.stats]
                                    else BorderSide(0, "transparent")
                                )
                            }
                        ),
                        data=star,
                        size=17 if star.type == StarType.minor else 25,
                        bgcolor=star.color,
                        left=star.coords[0],
                        top=star.coords[1],
                        on_click=self.change_lock_status,
                        on_hover=self.show_star_details,
                        on_long_press=self.max_branch,
                    )
                    for star in self.star_chart.get_stars()
                ],
            ],
            width=775,
            height=850,
        )
        self.map.controls.extend(
            [
                ScrollingFrame(
                    content=canvas.Canvas(
                        content=self.star_buttons,
                        shapes=[
                            *[
                                canvas.Path(
                                    [
                                        canvas.Path.MoveTo(*star.angle[0]),
                                        canvas.Path.LineTo(*star.angle[1]),
                                    ],
                                    paint=Paint(
                                        stroke_width=2,
                                        style=PaintingStyle.STROKE,
                                        color=(
                                            "#aabbcc"
                                            if not star.unlocked
                                            else "#ffd400"
                                        ),
                                    ),
                                )
                                for star in self.star_chart.get_stars()
                                if star.angle
                            ]
                        ],
                        width=775,
                        height=870,
                    ),
                    col={"xxl": 6},
                ),
                Column(
                    controls=[
                        Text(loc("Abilities"), size=22),
                        *(
                            [Text(loc(a)) for a in self.star_chart.activated_abilities]
                            or [Text("-")]
                        ),
                        Text(loc("Obtainables"), size=22),
                        *(
                            [
                                Text(f"{v}x  {loc(k)}")
                                for k, v in self.star_chart.activated_obtainables.items()
                            ]
                            or [Text("-")]
                        ),
                        ResponsiveRow(
                            controls=[
                                Dropdown(
                                    value=self.selected_stat or "none",
                                    options=[
                                        dropdown.Option(key="none", text="[None]"),
                                        *[
                                            dropdown.Option(key=stat, text=loc(stat))
                                            for stat in self.star_chart.stats_list
                                        ],
                                    ],
                                    label=loc("Find stats"),
                                    on_change=self.change_selected_stat,
                                    width=250,
                                    col={"xxl": 4},
                                ),
                                TextField(
                                    hint_text=loc("Insert build string"),
                                    width=250,
                                    on_change=self.set_star_chart_build,
                                    col={"xxl": 4},
                                ),
                                ElevatedButton(
                                    loc("Copy build"),
                                    width=250,
                                    disabled=not bool(
                                        self.star_chart.activated_stars_count
                                    ),
                                    on_click=self.copy_star_chart_build,
                                    col={"xxl": 4},
                                ),
                                ResponsiveRow(
                                    controls=[
                                        Column(
                                            controls=[
                                                Text(loc("Stats"), size=22),
                                                *(
                                                    [
                                                        DataTable(
                                                            heading_row_height=0,
                                                            data_row_min_height=40,
                                                            columns=[
                                                                DataColumn(Text()),
                                                                DataColumn(Text()),
                                                            ],
                                                            rows=[
                                                                DataRow(
                                                                    cells=[
                                                                        DataCell(
                                                                            Text(
                                                                                loc(k),
                                                                                size=13,
                                                                            )
                                                                        ),
                                                                        DataCell(
                                                                            Text(
                                                                                str(
                                                                                    v[0]
                                                                                )
                                                                                + (
                                                                                    f"%"
                                                                                    if v[
                                                                                        1
                                                                                    ]
                                                                                    else ""
                                                                                ),
                                                                                size=13,
                                                                            )
                                                                        ),
                                                                    ]
                                                                )
                                                                for k, v in self.star_chart.activated_stats.items()
                                                            ],
                                                        )
                                                    ]
                                                    if self.star_chart.activated_stats
                                                    else [Text("-")]
                                                ),
                                            ],
                                            col={"xxl": 5.5},
                                        ),
                                        self.star_details,
                                    ]
                                ),
                            ],
                            vertical_alignment="center",
                        ),
                    ],
                    col={"xxl": 6},
                ),
            ]
        )

    def setup_events(self): ...

    async def change_lock_status(self, event):
        staged_lock = event.control.data.stage_lock(self.star_chart)
        if staged_lock <= 0:
            event.control.data.switch_lock()
        else:
            await self.page.snack_bar.show(
                loc(
                    "Activating this star exceeds max of {MaxNode} by {StagedLock}"
                ).format(MaxNode=self.star_chart.max_nodes, StagedLock=staged_lock),
                color="red",
            )
        self.setup_controls()
        await self.page.update_async()

    async def reset_chart(self, _):
        self.star_chart = get_star_chart(files_cache["star_chart.json"])
        self.setup_controls()
        await self.page.update_async()

    async def show_star_details(self, event):
        star = event.control.data
        if event.data == "true":
            self.star_details.controls = [
                Column(
                    controls=[
                        Column(
                            controls=[
                                Text(loc(star.full_name), text_align="center", size=20)
                            ],
                            alignment="center",
                            horizontal_alignment="center",
                        ),
                        Column(
                            controls=[
                                *(
                                    [
                                        Divider(),
                                        Text(loc("Stats"), size=14),
                                        DataTable(
                                            heading_row_height=0,
                                            data_row_min_height=30,
                                            columns=[
                                                DataColumn(Text()),
                                                DataColumn(Text()),
                                            ],
                                            rows=[
                                                DataRow(
                                                    cells=[
                                                        DataCell(Text(loc(k))),
                                                        DataCell(
                                                            Text(
                                                                str(v[0])
                                                                + (f"%" if v[1] else "")
                                                            )
                                                        ),
                                                    ]
                                                )
                                                for k, v in star.format_stats.items()
                                            ],
                                        ),
                                    ]
                                    if star.stats
                                    else []
                                ),
                                *(
                                    [
                                        Divider(),
                                        Text(loc("Abilities"), size=14),
                                        DataTable(
                                            heading_row_height=0,
                                            data_row_min_height=80,
                                            columns=[DataColumn(Text())],
                                            rows=[
                                                DataRow(cells=[DataCell(Text(loc(v)))])
                                                for v in star.abilities
                                            ],
                                        ),
                                    ]
                                    if star.abilities
                                    else []
                                ),
                                *(
                                    [
                                        Divider(),
                                        Text(loc("Obtainables"), size=14),
                                        DataTable(
                                            heading_row_height=0,
                                            data_row_min_height=50,
                                            columns=[DataColumn(Text())],
                                            rows=[
                                                DataRow(cells=[DataCell(Text(loc(v)))])
                                                for v in star.obtainables
                                            ],
                                        ),
                                    ]
                                    if star.obtainables
                                    else []
                                ),
                            ]
                        ),
                    ]
                )
            ]
        else:
            self.star_details.controls.clear()
        await self.map.update_async()

    async def max_branch(self, event):
        if event.control.data.type != StarType.root:
            return
        if self.star_chart.activated_stars_count != 0:
            return
        for star in self.star_chart.get_stars():
            if star.constellation == event.control.data.constellation:
                star.unlock()
        self.setup_controls()
        await self.map.update_async()

    async def change_selected_stat(self, event):
        self.selected_stat = event.control.value
        for button in self.star_buttons.controls:
            if isinstance(button, RoundButton):
                button.style = None
        for button in self.star_buttons.controls:
            if isinstance(button, RoundButton):
                for stat in button.data.stats:
                    if stat["name"] == event.control.value:
                        button.style = ButtonStyle(
                            side={
                                MaterialState.DEFAULT: (
                                    BorderSide(3, "yellow")
                                    if self.selected_stat
                                    in [stat["name"] for stat in button.data.stats]
                                    else BorderSide(0, "transparent")
                                )
                            }
                        )
                        break
        await self.star_buttons.update_async()

    async def copy_star_chart_build(self, _):
        build_id = await self.star_chart.get_build()
        await self.page.set_clipboard_async("SC-" + build_id)
        await self.page.snack_bar.show(loc("Copied to clipboard"))

    async def set_star_chart_build(self, event):
        build_id = event.control.value
        self.star_chart = get_star_chart(files_cache["star_chart.json"])
        if await self.star_chart.from_string(build_id):
            event.control.value = None
            self.setup_controls()
            await self.page.snack_bar.show(f"Loaded build with id SC-{build_id}")
            await self.map.update_async()

    async def start_with_build_id(self, build_id):
        await self.star_chart.from_string(build_id)
        self.setup_controls()
        await self.map.update_async()
