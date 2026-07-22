import os
import csv
import re
from datetime import datetime
from functools import partial

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp, sp
from kivy.graphics import Color, Line, Rectangle, Ellipse
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.text import Label as CoreLabel

from database import Database

PRIMARY = (0.13, 0.59, 0.95, 1)
PRIMARY_DARK = (0.10, 0.46, 0.82, 1)
ACCENT = (1, 0.25, 0.50, 1)
BG = (0.96, 0.96, 0.96, 1)
CARD_BG = (1, 1, 1, 1)
TEXT_COLOR = (0.13, 0.13, 0.13, 1)
TEXT_SECONDARY = (0.46, 0.46, 0.46, 1)
DANGER = (0.90, 0.30, 0.24, 1)
SUCCESS = (0.30, 0.69, 0.31, 1)
WARNING = (1, 0.60, 0.0, 1)

if platform == 'android':
    from jnius import autoclass
    Toast = autoclass('android.widget.Toast')
    context = autoclass('org.kivy.android.PythonActivity').mActivity

    def show_toast(msg):
        Toast.makeText(context, msg, Toast.LENGTH_SHORT).show()
else:
    def show_toast(msg):
        print(msg)


class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.border = (dp(12), dp(12), dp(12), dp(12))
        self.halign = 'center'
        self.valign = 'middle'


class StatCard(BoxLayout):
    def __init__(self, title, value, unit='', color=PRIMARY, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(90)
        self.padding = dp(12)
        self.spacing = dp(4)

        with self.canvas.before:
            Color(*color, 0.08)
            self._rect = Rectangle(pos=self.pos, size=self.size)
            Color(*color, 1)
            self._line = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, dp(8)], width=1.5)

        self.bind(pos=self._update_rect, size=self._update_rect)

        lbl_title = Label(
            text=title.upper(),
            font_size=sp(11),
            color=color,
            size_hint_y=None,
            height=dp(18),
            halign='center',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))

        self.add_widget(lbl_title)

        val_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(4))
        val_box.add_widget(Widget(size_hint_x=0.1))

        lbl_val = Label(
            text=str(value),
            font_size=sp(28),
            bold=True,
            color=TEXT_COLOR,
            halign='right',
            valign='middle'
        )
        lbl_val.bind(size=lbl_val.setter('text_size'))

        lbl_unit = Label(
            text=unit,
            font_size=sp(14),
            color=TEXT_SECONDARY,
            halign='left',
            valign='bottom'
        )
        lbl_unit.bind(size=lbl_unit.setter('text_size'))

        val_box.add_widget(lbl_val)
        val_box.add_widget(lbl_unit)

        self.add_widget(val_box)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = [self.x, self.y, self.width, self.height, dp(8)]


class LineChart(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_points = []
        self.line_color = PRIMARY
        self.fill_color = (0.13, 0.59, 0.95, 0.12)
        self.padding_inner = dp(8)
        self.bottom_margin = dp(36)
        self.left_margin = dp(48)
        self.right_margin = dp(12)
        self.top_margin = dp(8)
        self.value_labels = []
        self.date_labels = []
        self._scheduled = None

    def set_data(self, data_points, line_color=None, label=''):
        self.data_points = data_points
        if line_color:
            self.line_color = line_color
            self.fill_color = (*line_color[:3], 0.12)
        if self._scheduled:
            Clock.unschedule(self._scheduled)
        self._scheduled = Clock.schedule_once(self._deferred_draw, 0.05)

    def _deferred_draw(self, *args):
        self._scheduled = None
        self.draw()

    def draw(self):
        self.canvas.clear()
        for child in self.value_labels + self.date_labels:
            if child in self.children:
                self.remove_widget(child)
        self.value_labels = []
        self.date_labels = []

        if not self.data_points:
            with self.canvas:
                Color(0.7, 0.7, 0.7, 1)
                lbl = CoreLabel(text='No data', font_size=sp(16))
                lbl.refresh()
                Rectangle(
                    texture=lbl.texture,
                    pos=(self.center_x - lbl.texture.width / 2, self.center_y - lbl.texture.height / 2),
                    size=lbl.texture.size
                )
            return

        values = [p[1] for p in self.data_points]
        if not values:
            return

        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val if max_val != min_val else 1

        chart_x = self.x + self.left_margin
        chart_y = self.y + self.bottom_margin
        chart_w = self.width - self.left_margin - self.right_margin
        chart_h = self.height - self.bottom_margin - self.top_margin

        if chart_w <= 0 or chart_h <= 0:
            return

        num_ticks = 4
        tick_step = val_range / num_ticks

        with self.canvas:
            Color(0.92, 0.92, 0.92, 1)
            for i in range(num_ticks + 1):
                y_pos = chart_y + (i / num_ticks) * chart_h
                Line(points=[chart_x, y_pos, chart_x + chart_w, y_pos], width=0.5)

            Color(0.92, 0.92, 0.92, 1)
            num_x_ticks = min(len(self.data_points) - 1, 6)
            if num_x_ticks > 0:
                for i in range(num_x_ticks + 1):
                    x_pos = chart_x + (i / num_x_ticks) * chart_w
                    Line(points=[x_pos, chart_y, x_pos, chart_y + chart_h], width=0.5)

        for i in range(num_ticks + 1):
            val = min_val + i * tick_step
            y_pos = chart_y + (i / num_ticks) * chart_h
            lbl = Label(
                text=str(int(val)),
                font_size=sp(10),
                color=TEXT_SECONDARY,
                size_hint=(None, None),
                size=(self.left_margin - dp(4), dp(18)),
                pos=(self.x, y_pos - dp(9)),
                halign='right',
                valign='middle'
            )
            self.value_labels.append(lbl)
            self.add_widget(lbl)

        num_x_labels = min(len(self.data_points), 5)
        step = max(1, len(self.data_points) // num_x_labels)
        for i in range(0, len(self.data_points), step):
            x_pos = chart_x + (i / max(1, len(self.data_points) - 1)) * chart_w
            label_text = self.data_points[i][0]
            if len(label_text) > 8:
                label_text = label_text[-5:]
            lbl = Label(
                text=label_text,
                font_size=sp(8),
                color=TEXT_SECONDARY,
                size_hint=(None, None),
                size=(dp(60), dp(20)),
                pos=(x_pos - dp(30), self.y),
                halign='center',
                valign='top'
            )
            self.date_labels.append(lbl)
            self.add_widget(lbl)

        points = []
        for i, (_, val) in enumerate(self.data_points):
            x = chart_x + (i / max(1, len(self.data_points) - 1)) * chart_w
            y = chart_y + ((val - min_val) / val_range) * chart_h
            points.extend([x, y])

        with self.canvas:
            Color(*self.line_color, 1)
            Line(points=points, width=2, smooth=True)

            for i in range(0, len(points), 2):
                Color(1, 1, 1, 1)
                Ellipse(pos=(points[i] - dp(4), points[i + 1] - dp(4)), size=(dp(8), dp(8)))
                Color(*self.line_color, 1)
                Ellipse(pos=(points[i] - dp(3), points[i + 1] - dp(3)), size=(dp(6), dp(6)))

            Color(0.7, 0.7, 0.7, 1)
            Line(points=[chart_x, chart_y, chart_x, chart_y + chart_h], width=1)
            Line(points=[chart_x, chart_y, chart_x + chart_w, chart_y], width=1)


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        scroll = ScrollView()
        self.content = BoxLayout(orientation='vertical', size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter('height'))
        scroll.add_widget(self.content)
        self.add_widget(scroll)

    def on_enter(self, *args):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        stats = app.db.get_statistics()
        latest = app.db.get_latest_reading()
        self.content.clear_widgets()

        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100), padding=[dp(20), dp(16), dp(20), dp(8)])
        with header.canvas.before:
            Color(*PRIMARY, 1)
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, v: setattr(header.canvas.before.children[-1], 'pos', header.pos))
        header.bind(size=lambda i, v: setattr(header.canvas.before.children[-1], 'size', header.size))

        title = Label(
            text='Blood Pressure Tracker',
            font_size=sp(22),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(36),
            halign='center',
            valign='middle'
        )
        title.bind(size=title.setter('text_size'))
        header.add_widget(title)

        if latest:
            subtitle = Label(
                text=f'Latest: {latest[3]}/{latest[4]} mmHg  |  HR: {latest[5]}  |  {latest[1][:10]}',
                font_size=sp(14),
                color=(1, 1, 1, 0.85),
                size_hint_y=None,
                height=dp(24),
                halign='center',
                valign='middle'
            )
            subtitle.bind(size=subtitle.setter('text_size'))
            header.add_widget(subtitle)
        else:
            subtitle = Label(
                text='No readings yet. Add your first one!',
                font_size=sp(14),
                color=(1, 1, 1, 0.85),
                size_hint_y=None,
                height=dp(24),
                halign='center',
                valign='middle'
            )
            subtitle.bind(size=subtitle.setter('text_size'))
            header.add_widget(subtitle)

        self.content.add_widget(header)

        stats_grid = GridLayout(cols=2, spacing=dp(10), padding=[dp(16), dp(12), dp(16), dp(8)],
                                 size_hint_y=None, height=dp(200))
        stats_grid.bind(minimum_height=stats_grid.setter('height'))

        if stats and stats[0] > 0:
            count, avg_sys, avg_dia, avg_hr, max_sys, min_sys, max_dia, min_dia = stats
            stats_grid.add_widget(StatCard('Total Readings', int(count), '', PRIMARY))
            stats_grid.add_widget(StatCard('Avg SYS', avg_sys, 'mmHg', (0.90, 0.30, 0.24, 1)))
            stats_grid.add_widget(StatCard('Avg DIA', avg_dia, 'mmHg', (0.30, 0.69, 0.31, 1)))
            stats_grid.add_widget(StatCard('Avg HR', avg_hr, 'bpm', (0.30, 0.40, 0.80, 1)))

        self.content.add_widget(stats_grid)

        btn_add = Button(
            text='+ ADD NEW READING',
            size_hint_y=None,
            height=dp(52),
            background_normal='',
            background_color=PRIMARY,
            color=(1, 1, 1, 1),
            font_size=sp(16),
            bold=True
        )
        btn_add.bind(on_press=lambda x: setattr(app.sm, 'current', 'add'))
        self.content.add_widget(btn_add)

        self.content.add_widget(Widget(size_hint_y=None, height=dp(20)))


class AddEditScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.editing_id = None
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', spacing=0)

        with layout.canvas.before:
            Color(*BG, 1)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self.bg_rect, 'pos', layout.pos))
        layout.bind(size=lambda i, v: setattr(self.bg_rect, 'size', layout.size))

        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(56), padding=[dp(16), dp(12), dp(16), dp(12)])
        with header.canvas.before:
            Color(*PRIMARY, 1)
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, v: setattr(header.canvas.before.children[-1], 'pos', header.pos))
        header.bind(size=lambda i, v: setattr(header.canvas.before.children[-1], 'size', header.size))

        self.header_label = Label(
            text='Add Reading',
            font_size=sp(20),
            bold=True,
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle'
        )
        self.header_label.bind(size=self.header_label.setter('text_size'))
        header.add_widget(self.header_label)
        layout.add_widget(header)

        scroll = ScrollView()
        form = GridLayout(cols=1, spacing=dp(12), padding=[dp(20), dp(16), dp(20), dp(16)],
                          size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        form.add_widget(Label(
            text='Date & Time', font_size=sp(14), color=TEXT_COLOR, bold=True,
            size_hint_y=None, height=dp(20), halign='left', valign='middle'
        ))
        self.timestamp_input = TextInput(
            text=datetime.now().strftime('%m/%d/%Y %I:%M %p'),
            size_hint_y=None, height=dp(48),
            multiline=False,
            font_size=sp(16),
            padding=[dp(12), dp(12)]
        )
        form.add_widget(self.timestamp_input)

        inputs_grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None, height=dp(100))

        sys_box = BoxLayout(orientation='vertical', spacing=dp(4))
        sys_box.add_widget(Label(text='SYS (systolic)', font_size=sp(13), color=TEXT_COLOR,
                                  size_hint_y=None, height=dp(18), halign='center', valign='middle'))
        self.sys_input = TextInput(
            text='', input_filter='int', multiline=False, font_size=sp(20),
            size_hint_y=None, height=dp(52),
            halign='center', padding=[dp(8), dp(12)]
        )
        sys_box.add_widget(self.sys_input)

        dia_box = BoxLayout(orientation='vertical', spacing=dp(4))
        dia_box.add_widget(Label(text='DIA (diastolic)', font_size=sp(13), color=TEXT_COLOR,
                                  size_hint_y=None, height=dp(18), halign='center', valign='middle'))
        self.dia_input = TextInput(
            text='', input_filter='int', multiline=False, font_size=sp(20),
            size_hint_y=None, height=dp(52),
            halign='center', padding=[dp(8), dp(12)]
        )
        dia_box.add_widget(self.dia_input)

        inputs_grid.add_widget(sys_box)
        inputs_grid.add_widget(dia_box)
        form.add_widget(inputs_grid)

        hr_box = BoxLayout(orientation='vertical', spacing=dp(4), size_hint_y=None, height=dp(80))
        hr_box.add_widget(Label(text='Heart Rate (bpm)', font_size=sp(13), color=TEXT_COLOR,
                                 size_hint_y=None, height=dp(18), halign='center', valign='middle'))
        self.hr_input = TextInput(
            text='', input_filter='int', multiline=False, font_size=sp(20),
            size_hint_y=None, height=dp(52),
            halign='center', padding=[dp(8), dp(12)]
        )
        hr_box.add_widget(self.hr_input)
        form.add_widget(hr_box)

        form.add_widget(Label(text='Notes (optional)', font_size=sp(13), color=TEXT_COLOR,
                               size_hint_y=None, height=dp(18), halign='left', valign='middle'))
        self.notes_input = TextInput(
            text='', size_hint_y=None, height=dp(60),
            multiline=True, font_size=sp(14),
            padding=[dp(8), dp(8)]
        )
        form.add_widget(self.notes_input)

        form.add_widget(Widget(size_hint_y=None, height=dp(8)))

        btn_layout = GridLayout(cols=2, spacing=dp(12), size_hint_y=None, height=dp(48))

        self.save_btn = Button(
            text='SAVE', font_size=sp(16), bold=True,
            background_normal='', background_color=PRIMARY,
            color=(1, 1, 1, 1)
        )
        self.save_btn.bind(on_press=self.save_reading)

        self.cancel_btn = Button(
            text='CANCEL', font_size=sp(16),
            background_normal='', background_color=(0.8, 0.8, 0.8, 1),
            color=TEXT_COLOR
        )
        self.cancel_btn.bind(on_press=self.go_back)

        btn_layout.add_widget(self.cancel_btn)
        btn_layout.add_widget(self.save_btn)
        form.add_widget(btn_layout)

        form.add_widget(Widget(size_hint_y=None, height=dp(20)))

        scroll.add_widget(form)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def save_reading(self, *args):
        app = App.get_running_app()
        timestamp = self.timestamp_input.text.strip()
        sys_val = self.sys_input.text.strip()
        dia_val = self.dia_input.text.strip()
        hr_val = self.hr_input.text.strip()
        notes = self.notes_input.text.strip()

        if not timestamp or not sys_val or not dia_val or not hr_val:
            popup = Popup(title='Error', content=Label(text='Please fill in all required fields'),
                          size_hint=(0.8, 0.4))
            popup.open()
            return

        try:
            sys_val = int(sys_val)
            dia_val = int(dia_val)
            hr_val = int(hr_val)
        except ValueError:
            popup = Popup(title='Error', content=Label(text='SYS, DIA, and HR must be numbers'),
                          size_hint=(0.8, 0.4))
            popup.open()
            return

        try:
            parsed_ts = self._parse_timestamp(timestamp)
            timestamp = parsed_ts
        except:
            popup = Popup(title='Error', content=Label(
                text=f'Invalid date format. Use MM/DD/YYYY HH:MM AM/PM\nExample: 07/22/2026 02:30 PM'),
                          size_hint=(0.8, 0.4))
            popup.open()
            return

        if self.editing_id:
            app.db.update_reading(self.editing_id, timestamp, sys_val, dia_val, hr_val, notes)
            show_toast('Reading updated!')
        else:
            app.db.add_reading(timestamp, sys_val, dia_val, hr_val, notes)
            show_toast('Reading added!')

        self.clear_form()
        app.sm.current = 'readings'

    def _parse_timestamp(self, ts_str):
        formats = [
            '%m/%d/%Y %I:%M %p',
            '%m/%d/%Y %I:%M%p',
            '%m/%d/%Y %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %I:%M %p',
            '%m/%d/%y %I:%M %p',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        raise ValueError(f'Cannot parse timestamp: {ts_str}')

    def go_back(self, *args):
        app = App.get_running_app()
        self.clear_form()
        app.sm.current = 'readings'

    def clear_form(self):
        self.editing_id = None
        self.timestamp_input.text = datetime.now().strftime('%m/%d/%Y %I:%M %p')
        self.sys_input.text = ''
        self.dia_input.text = ''
        self.hr_input.text = ''
        self.notes_input.text = ''
        self.header_label.text = 'Add Reading'

    def load_reading(self, reading_id):
        app = App.get_running_app()
        reading = app.db.get_reading(reading_id)
        if reading:
            self.editing_id = reading_id
            try:
                dt = datetime.strptime(reading[1], '%Y-%m-%d %H:%M:%S')
                self.timestamp_input.text = dt.strftime('%m/%d/%Y %I:%M %p')
            except:
                self.timestamp_input.text = reading[1]
            self.sys_input.text = str(reading[2])
            self.dia_input.text = str(reading[3])
            self.hr_input.text = str(reading[4])
            self.notes_input.text = reading[5] if reading[5] else ''
            self.header_label.text = 'Edit Reading'

    def on_enter(self, *args):
        pass


class ReadingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content = BoxLayout(orientation='vertical')
        self.add_widget(self.content)

    def on_enter(self, *args):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        readings = app.db.get_all_readings()
        self.content.clear_widgets()

        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(56), padding=[dp(16), dp(12), dp(16), dp(12)])
        with header.canvas.before:
            Color(*PRIMARY, 1)
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, v: setattr(header.canvas.before.children[-1], 'pos', header.pos))
        header.bind(size=lambda i, v: setattr(header.canvas.before.children[-1], 'size', header.size))

        h_label = Label(
            text=f'Readings ({len(readings)})',
            font_size=sp(20),
            bold=True,
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle'
        )
        h_label.bind(size=h_label.setter('text_size'))
        header.add_widget(h_label)
        self.content.add_widget(header)

        if not readings:
            no_data = Label(
                text='No readings yet.\nTap + to add your first one!',
                font_size=sp(16),
                color=TEXT_SECONDARY,
                halign='center',
                valign='middle'
            )
            self.content.add_widget(no_data)
            return

        scroll = ScrollView()
        list_layout = GridLayout(cols=1, spacing=dp(6), padding=[dp(12), dp(8), dp(12), dp(8)],
                                  size_hint_y=None)
        list_layout.bind(minimum_height=list_layout.setter('height'))

        for reading in readings:
            card = self._make_reading_card(reading)
            list_layout.add_widget(card)

        scroll.add_widget(list_layout)
        self.content.add_widget(scroll)

    def _make_reading_card(self, reading):
        rid, ts, sys_val, dia_val, hr_val, notes = reading

        try:
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            display_date = dt.strftime('%b %d, %Y')
            display_time = dt.strftime('%I:%M %p')
        except:
            display_date = ts[:10]
            display_time = ts[11:16] if len(ts) > 16 else ''

        card = BoxLayout(orientation='vertical', size_hint_y=None, padding=[dp(14), dp(10), dp(14), dp(10)],
                         spacing=dp(6))
        card.bind(minimum_height=card.setter('height'))

        with card.canvas.before:
            Color(1, 1, 1, 1)
            card._rect = Rectangle(pos=card.pos, size=card.size)
            Color(0.88, 0.88, 0.88, 1)
            card._line = Line(rounded_rectangle=[card.x, card.y, card.width, card.height, dp(8)], width=1)
        card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        top_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28), spacing=dp(8))

        date_label = Label(
            text=f'{display_date}  {display_time}',
            font_size=sp(14),
            color=TEXT_COLOR,
            bold=True,
            halign='left',
            valign='middle',
            size_hint_x=0.6
        )
        date_label.bind(size=date_label.setter('text_size'))

        btn_edit = Button(
            text='EDIT',
            size_hint_x=0.2,
            font_size=sp(11),
            background_normal='',
            background_color=(0.3, 0.4, 0.8, 0.15),
            color=(0.3, 0.4, 0.8, 1)
        )
        btn_edit.bind(on_press=lambda x, r=reading: self._edit_reading(r[0]))

        btn_del = Button(
            text='DEL',
            size_hint_x=0.2,
            font_size=sp(11),
            background_normal='',
            background_color=(0.9, 0.3, 0.24, 0.15),
            color=(0.9, 0.3, 0.24, 1)
        )
        btn_del.bind(on_press=lambda x, r=reading: self._delete_reading(r[0]))

        top_row.add_widget(date_label)
        top_row.add_widget(btn_edit)
        top_row.add_widget(btn_del)

        card.add_widget(top_row)

        values_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), spacing=dp(16))

        sys_color = DANGER if sys_val >= 140 else (0.8, 0.6, 0.0, 1) if sys_val >= 130 else SUCCESS
        dia_color = DANGER if dia_val >= 90 else (0.8, 0.6, 0.0, 1) if dia_val >= 80 else SUCCESS

        values_row.add_widget(Label(
            text=f'SYS {sys_val}', font_size=sp(18), bold=True, color=sys_color,
            halign='center', valign='middle'
        ))
        values_row.add_widget(Label(
            text=f'DIA {dia_val}', font_size=sp(18), bold=True, color=dia_color,
            halign='center', valign='middle'
        ))
        values_row.add_widget(Label(
            text=f'HR {hr_val}', font_size=sp(16), color=(0.3, 0.4, 0.8, 1),
            halign='center', valign='middle'
        ))

        card.add_widget(values_row)

        if notes:
            notes_label = Label(
                text=notes, font_size=sp(12), color=TEXT_SECONDARY,
                size_hint_y=None, height=dp(20), halign='left', valign='middle'
            )
            notes_label.bind(size=notes_label.setter('text_size'))
            card.add_widget(notes_label)

        return card

    def _update_card_rect(self, instance, value):
        if hasattr(instance, '_rect'):
            instance._rect.pos = instance.pos
            instance._rect.size = instance.size
        if hasattr(instance, '_line'):
            instance._line.rounded_rectangle = [instance.x, instance.y, instance.width, instance.height, dp(8)]

    def _edit_reading(self, reading_id):
        app = App.get_running_app()
        add_screen = app.sm.get_screen('add')
        add_screen.load_reading(reading_id)
        app.sm.current = 'add'

    def _delete_reading(self, reading_id):
        app = App.get_running_app()

        content = BoxLayout(orientation='vertical', spacing=dp(16), padding=dp(20))
        content.add_widget(Label(
            text='Delete this reading?',
            font_size=sp(16), halign='center', valign='middle'
        ))

        btn_row = BoxLayout(orientation='horizontal', spacing=dp(12), size_hint_y=None, height=dp(44))

        popup = Popup(title='Confirm Delete', content=content, size_hint=(0.8, 0.35))

        btn_yes = Button(text='DELETE', background_normal='', background_color=DANGER, color=(1, 1, 1, 1))
        btn_no = Button(text='CANCEL', background_normal='', background_color=(0.8, 0.8, 0.8, 1), color=TEXT_COLOR)

        btn_yes.bind(on_press=lambda x: self._confirm_delete(reading_id, popup))
        btn_no.bind(on_press=lambda x: popup.dismiss())

        btn_row.add_widget(btn_no)
        btn_row.add_widget(btn_yes)
        content.add_widget(btn_row)

        popup.open()

    def _confirm_delete(self, reading_id, popup):
        popup.dismiss()
        app = App.get_running_app()
        app.db.delete_reading(reading_id)
        show_toast('Reading deleted')
        self.refresh()


class ChartsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_metric = 'sys'
        self._built = False

    def on_enter(self, *args):
        if not self._built:
            self._build_ui()
            self._built = True
        self.refresh()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')
        with layout.canvas.before:
            Color(*BG, 1)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self.bg_rect, 'pos', layout.pos))
        layout.bind(size=lambda i, v: setattr(self.bg_rect, 'size', layout.size))

        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(56), padding=[dp(16), dp(12), dp(16), dp(12)])
        with header.canvas.before:
            Color(*PRIMARY, 1)
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, v: setattr(header.canvas.before.children[-1], 'pos', header.pos))
        header.bind(size=lambda i, v: setattr(header.canvas.before.children[-1], 'size', header.size))

        h_label = Label(text='Trends', font_size=sp(20), bold=True, color=(1, 1, 1, 1),
                         halign='center', valign='middle')
        h_label.bind(size=h_label.setter('text_size'))
        header.add_widget(h_label)
        layout.add_widget(header)

        toggle_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48),
                                spacing=dp(8), padding=[dp(12), dp(8), dp(12), dp(8)])
        metrics = [
            ('SYS', 'sys', DANGER),
            ('DIA', 'dia', SUCCESS),
            ('HR', 'hr', (0.3, 0.4, 0.8, 1)),
        ]
        self.toggle_buttons = []
        for label, key, color in metrics:
            btn = Button(
                text=label, font_size=sp(15), bold=True,
                background_normal='', background_color=(*color[:3], 0.15),
                color=color
            )
            btn.bind(on_press=lambda x, k=key, c=color: self._switch_metric(k, c))
            toggle_bar.add_widget(btn)
            self.toggle_buttons.append((btn, key, color))

        layout.add_widget(toggle_bar)

        self.chart = LineChart(size_hint=(1, 1), size_hint_min_y=dp(250))
        layout.add_widget(self.chart)

        self.add_widget(layout)

    def _switch_metric(self, metric, color):
        self.current_metric = metric
        for btn, key, btn_color in self.toggle_buttons:
            if key == metric:
                btn.background_color = (*btn_color[:3], 0.25)
                btn.color = btn_color
            else:
                btn.background_color = (*btn_color[:3], 0.08)
                btn.color = (*btn_color[:3], 0.6)
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        readings = app.db.get_all_readings()

        if not readings:
            self.chart.set_data([], PRIMARY)
            return

        data_points = []
        for r in readings:
            try:
                dt = datetime.strptime(r[1], '%Y-%m-%d %H:%M:%S')
                label = dt.strftime('%m/%d')
            except:
                label = r[1][:5]

            if self.current_metric == 'sys':
                val = r[2]
                color = DANGER
            elif self.current_metric == 'dia':
                val = r[3]
                color = SUCCESS
            else:
                val = r[4]
                color = (0.3, 0.4, 0.8, 1)

            data_points.append((label, val))

        self.chart.set_data(data_points, color)


class ExportScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content = BoxLayout(orientation='vertical')
        self.add_widget(self.content)

    def on_enter(self, *args):
        self.refresh()

    def refresh(self):
        self.content.clear_widgets()

        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(56), padding=[dp(16), dp(12), dp(16), dp(12)])
        with header.canvas.before:
            Color(*PRIMARY, 1)
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, v: setattr(header.canvas.before.children[-1], 'pos', header.pos))
        header.bind(size=lambda i, v: setattr(header.canvas.before.children[-1], 'size', header.size))

        h_label = Label(text='Export Data', font_size=sp(20), bold=True, color=(1, 1, 1, 1),
                         halign='center', valign='middle')
        h_label.bind(size=h_label.setter('text_size'))
        header.add_widget(h_label)
        self.content.add_widget(header)

        info = Label(
            text='Export all your blood pressure readings\nto a CSV file for sharing or backup.',
            font_size=sp(15), color=TEXT_COLOR,
            halign='center', valign='middle',
            size_hint_y=None, height=dp(80)
        )
        info.bind(size=info.setter('text_size'))
        self.content.add_widget(info)

        app = App.get_running_app()
        stats = app.db.get_statistics()
        if stats and stats[0] > 0:
            stats_text = f'Total readings to export: {stats[0]}'
        else:
            stats_text = 'No readings to export.'
        stats_label = Label(text=stats_text, font_size=sp(14), color=TEXT_SECONDARY,
                             size_hint_y=None, height=dp(40), halign='center', valign='middle')
        stats_label.bind(size=stats_label.setter('text_size'))
        self.content.add_widget(stats_label)

        self.content.add_widget(Widget(size_hint_y=None, height=dp(20)))

        export_btn = Button(
            text='EXPORT TO CSV',
            size_hint_y=None, height=dp(52),
            background_normal='', background_color=SUCCESS,
            color=(1, 1, 1, 1), font_size=sp(16), bold=True
        )
        export_btn.bind(on_press=self.do_export)
        self.content.add_widget(export_btn)

        self.content.add_widget(Widget(size_hint_y=None, height=dp(40)))

        share_hint = Label(
            text='The CSV file will be saved in your Downloads folder.',
            font_size=sp(12), color=TEXT_SECONDARY,
            halign='center', valign='middle',
            size_hint_y=None, height=dp(60)
        )
        share_hint.bind(size=share_hint.setter('text_size'))
        self.content.add_widget(share_hint)

    def do_export(self, *args):
        app = App.get_running_app()
        try:
            if platform == 'android':
                from jnius import autoclass
                Environment = autoclass('android.os.Environment')
                export_dir = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
            else:
                export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
            os.makedirs(export_dir, exist_ok=True)
            filename = f'blood_pressure_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            filepath = os.path.join(export_dir, filename)
            app.db.export_csv(filepath)
            show_toast(f'Exported to Downloads: {filename}')
        except Exception as e:
            popup = Popup(title='Export Error', content=Label(text=str(e)),
                          size_hint=(0.8, 0.4))
            popup.open()


class ScanScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')
        with layout.canvas.before:
            Color(*BG, 1)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self.bg_rect, 'pos', layout.pos))
        layout.bind(size=lambda i, v: setattr(self.bg_rect, 'size', layout.size))

        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(56), padding=[dp(16), dp(12), dp(16), dp(12)])
        with header.canvas.before:
            Color(*PRIMARY, 1)
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, v: setattr(header.canvas.before.children[-1], 'pos', header.pos))
        header.bind(size=lambda i, v: setattr(header.canvas.before.children[-1], 'size', header.size))

        h_label = Label(text='Scan Reading', font_size=sp(20), bold=True, color=(1, 1, 1, 1),
                         halign='center', valign='middle')
        h_label.bind(size=h_label.setter('text_size'))
        header.add_widget(h_label)

        settings_btn = Button(text='\u2699', font_size=sp(22), size_hint=(None, None), size=(dp(44), dp(44)),
                               background_normal='', background_color=(1, 1, 1, 0.2), color=(1, 1, 1, 1))
        settings_btn.bind(on_press=self._open_settings)
        header.add_widget(settings_btn)

        layout.add_widget(header)

        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(16), padding=[dp(20), dp(20), dp(20), dp(20)])
        content.bind(minimum_height=content.setter('height'))

        self.api_status = Label(
            text='',
            font_size=sp(12), color=TEXT_SECONDARY,
            size_hint_y=None, height=dp(20), halign='center', valign='middle'
        )
        self.api_status.bind(size=self.api_status.setter('text_size'))
        content.add_widget(self.api_status)

        info = Label(
            text='Take a photo of your BP monitor display,\nthen enter the values manually below.\n(Optional: set an API key for auto-OCR)',
            font_size=sp(15), color=TEXT_COLOR,
            halign='center', valign='middle',
            size_hint_y=None, height=dp(90)
        )
        info.bind(size=info.setter('text_size'))
        content.add_widget(info)

        content.add_widget(Widget(size_hint_y=None, height=dp(10)))

        camera_btn = Button(
            text='\u25CB  TAKE PHOTO',
            size_hint_y=None, height=dp(60),
            background_normal='', background_color=PRIMARY,
            color=(1, 1, 1, 1), font_size=sp(17), bold=True
        )
        camera_btn.bind(on_press=self._take_photo)
        content.add_widget(camera_btn)

        content.add_widget(Widget(size_hint_y=None, height=dp(10)))

        gallery_btn = Button(
            text='\u25A1  CHOOSE FROM GALLERY',
            size_hint_y=None, height=dp(60),
            background_normal='', background_color=(0.3, 0.4, 0.8, 1),
            color=(1, 1, 1, 1), font_size=sp(17), bold=True
        )
        gallery_btn.bind(on_press=self._choose_gallery)
        content.add_widget(gallery_btn)

        content.add_widget(Widget(size_hint_y=None, height=dp(20)))

        self.result_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self.result_box.bind(minimum_height=self.result_box.setter('height'))
        content.add_widget(self.result_box)

        scroll.add_widget(content)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def on_enter(self, *args):
        self._update_api_status()

    def _update_api_status(self):
        from config import get_api_key
        key = get_api_key()
        if key:
            masked = key[:6] + '*' * (len(key) - 8) + key[-4:] if len(key) > 10 else '***'
            self.api_status.text = f'OCR: ON (\u2699 {masked})'
            self.api_status.color = SUCCESS
        else:
            self.api_status.text = 'OCR: OFF (tap \u2699 to enable auto-read)'
            self.api_status.color = TEXT_SECONDARY

    def _open_settings(self, *args):
        from config import get_api_key, set_api_key
        current_key = get_api_key()

        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)])
        content.add_widget(Label(text='Enter your Google Cloud Vision API key:',
                                 font_size=sp(14), color=TEXT_COLOR, size_hint_y=None, height=dp(24),
                                 halign='left', valign='middle'))
        content.add_widget(Label(text='(or leave blank to clear)',
                                 font_size=sp(11), color=TEXT_SECONDARY, size_hint_y=None, height=dp(16),
                                 halign='left', valign='middle'))

        text_input = TextInput(text=current_key, size_hint_y=None, height=dp(48),
                                multiline=False, font_size=sp(14), padding=[dp(8), dp(12)])

        btn_row = BoxLayout(orientation='horizontal', spacing=dp(12), size_hint_y=None, height=dp(48))

        popup = Popup(title='API Key Settings', content=content, size_hint=(0.9, 0.45))

        def save_key(*args):
            set_api_key(text_input.text.strip())
            self._update_api_status()
            show_toast('API key saved')
            popup.dismiss()

        save_btn = Button(text='SAVE', background_normal='', background_color=PRIMARY, color=(1, 1, 1, 1))
        save_btn.bind(on_press=save_key)

        cancel_btn = Button(text='CANCEL', background_normal='', background_color=(0.8, 0.8, 0.8, 1), color=TEXT_COLOR)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())

        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(save_btn)

        content.add_widget(text_input)
        content.add_widget(Widget(size_hint_y=None, height=dp(8)))
        content.add_widget(btn_row)

        popup.open()

    def _take_photo(self, *args):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                MediaStore = autoclass('android.provider.MediaStore')
                intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                uri = self._get_temp_uri()
                intent.putExtra(MediaStore.EXTRA_OUTPUT, uri)
                PythonActivity.mActivity.startActivityForResult(intent, 1001)
            except Exception as e:
                self._fallback_file_chooser('photo')
        else:
            self._fallback_file_chooser('photo')

    def _choose_gallery(self, *args):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.setType('image/*')
                PythonActivity.mActivity.startActivityForResult(intent, 1002)
            except Exception as e:
                self._fallback_file_chooser('gallery')
        else:
            self._fallback_file_chooser('gallery')

    def _get_temp_uri(self):
        from jnius import autoclass
        context = autoclass('org.kivy.android.PythonActivity').mActivity
        FileProvider = autoclass('androidx.core.content.FileProvider')
        File = autoclass('java.io.File')
        temp_dir = context.getCacheDir()
        temp_file = File(temp_dir, 'bp_photo_' + str(int(datetime.now().timestamp())) + '.jpg')
        return FileProvider.getUriForFile(context, context.getPackageName() + '.fileprovider', temp_file)

    def _fallback_file_chooser(self, source_type):
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.modalview import ModalView

        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=[dp(8), dp(8), dp(8), dp(8)])
        fc = FileChooserListView(path=os.path.expanduser('~'), filters=['*.png', '*.jpg', '*.jpeg'])
        btn_select = Button(text='SELECT', size_hint_y=None, height=dp(48),
                             background_normal='', background_color=PRIMARY, color=(1, 1, 1, 1))
        btn_close = Button(text='CANCEL', size_hint_y=None, height=dp(48),
                           background_normal='', background_color=(0.8, 0.8, 0.8, 1), color=TEXT_COLOR)

        btn_row = BoxLayout(orientation='horizontal', spacing=dp(12), size_hint_y=None, height=dp(48))

        popup = Popup(title='Select Image', content=content, size_hint=(0.95, 0.85))

        def select(*args):
            if fc.selection:
                popup.dismiss()
                self._process_image(fc.selection[0])

        btn_select.bind(on_press=select)
        btn_close.bind(on_press=lambda x: popup.dismiss())
        btn_row.add_widget(btn_close)
        btn_row.add_widget(btn_select)

        content.add_widget(fc)
        content.add_widget(btn_row)

        popup.open()

    def _process_image(self, image_path):
        from config import get_api_key
        from ocr_helper import parse_ocr_text

        self.result_box.clear_widgets()
        loading = Label(
            text='Processing image...',
            font_size=sp(16), color=TEXT_COLOR,
            size_hint_y=None, height=dp(60),
            halign='center', valign='middle'
        )
        loading.bind(size=loading.setter('text_size'))
        self.result_box.add_widget(loading)
        Clock.schedule_once(lambda dt: self._do_process(image_path), 0.1)

    def _do_process(self, image_path):
        from config import get_api_key
        from ocr_helper import ocr_image, parse_ocr_text

        self.result_box.clear_widgets()
        api_key = get_api_key()
        parsed = {}
        raw_text = ''

        if api_key:
            try:
                raw_text = ocr_image(image_path)
                parsed = parse_ocr_text(raw_text)
            except Exception as e:
                pass

        self._show_confirmation(parsed, raw_text)

    def _show_confirmation(self, parsed, raw_text):
        self.result_box.clear_widgets()

        card = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8), padding=[dp(16), dp(16), dp(16), dp(16)])
        card.bind(minimum_height=card.setter('height'))
        with card.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=card.pos, size=card.size)
            Color(0.88, 0.88, 0.88, 1)
            Line(rounded_rectangle=[card.x, card.y, card.width, card.height, dp(8)], width=1)
        card.bind(pos=lambda i, v: self._update_card_bg(i, v),
                  size=lambda i, v: self._update_card_bg(i, v))

        label = Label(
            text='Extracted Values',
            font_size=sp(16), bold=True, color=TEXT_COLOR,
            size_hint_y=None, height=dp(24), halign='center', valign='middle'
        )
        label.bind(size=label.setter('text_size'))
        card.add_widget(label)

        parsed_ts = datetime.now()

        card.add_widget(Label(text='Timestamp', font_size=sp(12), color=TEXT_SECONDARY,
                              size_hint_y=None, height=dp(16), halign='left', valign='middle'))

        self.conf_ts = TextInput(
            text=parsed_ts.strftime('%m/%d/%Y %I:%M %p'),
            size_hint_y=None, height=dp(44), multiline=False, font_size=sp(16),
            padding=[dp(8), dp(8)]
        )
        card.add_widget(self.conf_ts)

        input_grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(80))

        def make_field_box(label, key):
            ti = TextInput(
                text=str(parsed.get(key, '')),
                input_filter='int', multiline=False, font_size=sp(20),
                halign='center', padding=[dp(4), dp(8)]
            )
            return ti

        self.conf_sys = make_field_box('SYS', 'sys')
        self.conf_dia = make_field_box('DIA', 'dia')
        self.conf_hr = make_field_box('HR', 'hr')

        for label, ti in [('SYS', self.conf_sys), ('DIA', self.conf_dia), ('HR', self.conf_hr)]:
            box = BoxLayout(orientation='vertical', spacing=dp(2))
            box.add_widget(Label(text=label, font_size=sp(11), color=TEXT_COLOR,
                                  size_hint_y=None, height=dp(16), halign='center', valign='middle'))
            box.add_widget(ti)
            input_grid.add_widget(box)

        card.add_widget(input_grid)

        btn_row = BoxLayout(orientation='horizontal', spacing=dp(12), size_hint_y=None, height=dp(48))
        save_btn = Button(text='SAVE READING', background_normal='', background_color=SUCCESS, color=(1, 1, 1, 1), bold=True)
        save_btn.bind(on_press=self._save_scanned)
        cancel_btn = Button(text='CANCEL', background_normal='', background_color=(0.8, 0.8, 0.8, 1), color=TEXT_COLOR)
        cancel_btn.bind(on_press=lambda x: self.result_box.clear_widgets())
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(save_btn)
        card.add_widget(btn_row)

        self.result_box.add_widget(card)

    def _update_card_bg(self, instance, value):
        for child in instance.canvas.before.children:
            if isinstance(child, Rectangle):
                child.pos = instance.pos
                child.size = instance.size
            elif isinstance(child, Line):
                child.rounded_rectangle = [instance.x, instance.y, instance.width, instance.height, dp(8)]

    def _save_scanned(self, *args):
        app = App.get_running_app()
        timestamp = self.conf_ts.text.strip()
        sys_val = self.conf_sys.text.strip()
        dia_val = self.conf_dia.text.strip()
        hr_val = self.conf_hr.text.strip()

        if not timestamp or not sys_val or not dia_val or not hr_val:
            popup = Popup(title='Error', content=Label(text='Please fill in all fields'),
                          size_hint=(0.8, 0.4))
            popup.open()
            return

        try:
            sys_val = int(sys_val)
            dia_val = int(dia_val)
            hr_val = int(hr_val)
        except ValueError:
            popup = Popup(title='Error', content=Label(text='Values must be numbers'),
                          size_hint=(0.8, 0.4))
            popup.open()
            return

        try:
            timestamp = self._parse_timestamp(timestamp)
        except ValueError:
            popup = Popup(title='Error', content=Label(
                text='Invalid date format. Use MM/DD/YYYY HH:MM AM/PM'),
                          size_hint=(0.8, 0.4))
            popup.open()
            return

        app.db.add_reading(timestamp, sys_val, dia_val, hr_val)
        show_toast('Reading saved from scan!')
        self.result_box.clear_widgets()
        confirm = Label(text='Reading saved!', font_size=sp(18), color=SUCCESS,
                         size_hint_y=None, height=dp(60), halign='center', valign='middle')
        confirm.bind(size=confirm.setter('text_size'))
        self.result_box.add_widget(confirm)

    def _parse_timestamp(self, ts_str):
        formats = [
            '%m/%d/%Y %I:%M %p',
            '%m/%d/%Y %I:%M%p',
            '%m/%d/%Y %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %I:%M %p',
            '%m/%d/%y %I:%M %p',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        raise ValueError(f'Cannot parse timestamp: {ts_str}')


class NavButton(ButtonBehavior, BoxLayout):
    def __init__(self, text, icon_text, screen_name, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(56)
        self.padding = [dp(4), dp(4)]
        self.spacing = dp(2)
        self.screen_name = screen_name

        self.icon = Label(
            text=icon_text,
            font_size=sp(20),
            size_hint_y=None,
            height=dp(26),
            halign='center',
            valign='middle',
            color=TEXT_SECONDARY
        )
        self.label = Label(
            text=text,
            font_size=sp(10),
            size_hint_y=None,
            height=dp(16),
            halign='center',
            valign='middle',
            color=TEXT_SECONDARY
        )
        self.add_widget(self.icon)
        self.add_widget(self.label)

        self.bind(on_press=self._navigate)

    def _navigate(self, *args):
        app = App.get_running_app()
        app.sm.current = self.screen_name
        self._update_active()

    def _update_active(self):
        app = App.get_running_app()
        is_active = app.sm.current == self.screen_name
        if is_active:
            self.icon.color = PRIMARY
            self.label.color = PRIMARY
        else:
            self.icon.color = TEXT_SECONDARY
            self.label.color = TEXT_SECONDARY


class BloodPressureApp(App):
    def build(self):
        db_path = os.path.join(self.user_data_dir, 'blood_pressure.db')
        self.db = Database(db_path)
        self.title = 'BP Tracker'

        Window.clearcolor = (1, 1, 1, 1)

        root = BoxLayout(orientation='vertical')

        self.sm = ScreenManager()
        self.sm.add_widget(DashboardScreen(name='dashboard'))
        self.sm.add_widget(ReadingsScreen(name='readings'))
        self.sm.add_widget(AddEditScreen(name='add'))
        self.sm.add_widget(ScanScreen(name='scan'))
        self.sm.add_widget(ChartsScreen(name='charts'))
        self.sm.add_widget(ExportScreen(name='export'))

        root.add_widget(self.sm)

        self.nav_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(56),
                                  spacing=0, padding=[0, 0, 0, 0])
        with self.nav_bar.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            self._nav_rect = Rectangle(pos=self.nav_bar.pos, size=self.nav_bar.size)
            Color(0.85, 0.85, 0.85, 1)
            Line(points=[self.nav_bar.x, self.nav_bar.y + self.nav_bar.height, self.nav_bar.x + self.nav_bar.width, self.nav_bar.y + self.nav_bar.height],
                 width=1)
        self.nav_bar.bind(pos=self._update_nav_bg, size=self._update_nav_bg)

        nav_items = [
            ('Home', '\u2302', 'dashboard'),
            ('List', '\u2630', 'readings'),
            ('Add', '+', 'add'),
            ('Scan', '\u25CB', 'scan'),
            ('Charts', '\u25A3', 'charts'),
            ('Export', '\u2913', 'export'),
        ]

        for text, icon, screen_name in nav_items:
            btn = NavButton(text, icon, screen_name)
            btn.size_hint_x = 1.0 / len(nav_items)
            self.nav_bar.add_widget(btn)

        root.add_widget(self.nav_bar)

        self.sm.bind(current=self._on_screen_changed)

        return root

    def _update_nav_bg(self, instance, value):
        if hasattr(self, '_nav_rect'):
            self._nav_rect.pos = instance.pos
            self._nav_rect.size = instance.size

    def _on_screen_changed(self, instance, value):
        for child in self.nav_bar.children:
            if isinstance(child, NavButton):
                child._update_active()

    def on_start(self):
        self._import_if_empty()

    def _import_if_empty(self):
        readings = self.db.get_all_readings()
        if len(readings) > 0:
            return

        md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'readings.md')
        if not os.path.exists(md_path):
            return

        try:
            count = import_from_markdown(md_path, self.db)
            if count > 0:
                show_toast(f'Imported {count} readings from your existing data!')
        except Exception as e:
            print(f'Auto-import failed: {e}')

    def on_stop(self):
        self.db.close()


def import_from_markdown(filepath, db):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    readings = []
    header_found = False

    for line in lines:
        line = line.strip()
        if line.startswith('|TIME|') or line.startswith('|Time|'):
            header_found = True
            continue
        if not header_found:
            continue
        if line.startswith('|-') or line == '' or line.startswith('|After '):
            continue
        if not line.startswith('|') or not line.endswith('|'):
            continue

        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]

        if len(parts) < 4:
            continue

        time_str, sys_str, dia_str, hr_str = parts[0], parts[1], parts[2], parts[3]

        time_str = time_str.strip()
        sys_str = sys_str.strip()
        dia_str = dia_str.strip()
        hr_str = hr_str.strip()

        try:
            sys_val = int(sys_str)
            dia_val = int(dia_str)
            hr_val = int(hr_str)
        except ValueError:
            continue

        time_formats = [
            '%I:%M %p %m/%d/%Y',
            '%I:%M%p %m/%d/%Y',
            '%I:%M %p %m/%d/%y',
            '%m/%d/%Y %I:%M %p',
            '%m/%d/%Y %H:%M',
        ]

        parsed_ts = None
        for fmt in time_formats:
            try:
                parsed_ts = datetime.strptime(time_str, fmt).strftime('%Y-%m-%d %H:%M:%S')
                break
            except ValueError:
                continue

        if parsed_ts is None:
            continue

        readings.append((parsed_ts, sys_val, dia_val, hr_val))

    count = 0
    for ts, sys_val, dia_val, hr_val in readings:
        db.add_reading(ts, sys_val, dia_val, hr_val)
        count += 1

    return count


if __name__ == '__main__':
    BloodPressureApp().run()
