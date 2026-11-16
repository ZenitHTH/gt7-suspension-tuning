"""World Circuits 3-step modal picker dialog (Continent -> Circuit -> Layout)."""
from typing import Callable, List, Optional, Sequence, TypeVar

from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from db.catalog import TRACK_CONTINENTS, CircuitSummary, TrackLayoutEntry
from gui.picker_dialog import StepPickerDialog, clear_layout, make_picker_button
from gui.service import TuningService

_CIRCUIT_COLUMNS = 3
_LAYOUT_COLUMNS = 2
_T = TypeVar('_T')


def _surface_tag(track: TrackLayoutEntry) -> Optional[str]:
    """Return 'Snow' or 'Dirt' surface tag for off-tarmac layouts, else None."""
    category = track.category.lower()
    text = f'{track.base_circuit} {track.name}'.lower()
    if category == 'snow' or (category == 'snow_dirt' and ('snow' in text or 'lake louise' in text)):
        return 'Snow'
    if category in ('dirt', 'snow_dirt'):
        return 'Dirt'
    return None


def format_layout_subtitle(track: TrackLayoutEntry) -> str:
    """Format distance, corner count, and surface/rain/oval tags for a layout."""
    turns_unit = 'turn' if track.num_corners == 1 else 'turns'
    parts: List[str] = [f'{track.length_km:.2f} km', f'{track.num_corners} {turns_unit}']
    if track.rain_supported:
        parts.append('Rain')
    if track.is_oval:
        parts.append('Oval')
    surface = _surface_tag(track)
    if surface:
        parts.append(surface)
    return ' · '.join(parts)


def _plural(count: int, singular: str, plural: str) -> str:
    """Format an integer count with singular or plural noun."""
    return f'{count} {singular if count == 1 else plural}'


def _populate_grid(container: QVBoxLayout, items: Sequence[_T], columns: int,
                   build_btn: Callable[[_T], QPushButton], empty_text: str) -> None:
    """Render `items` into `container` as a uniform grid or empty-state label."""
    clear_layout(container)
    if not items:
        container.addWidget(QLabel(empty_text, objectName='pickerEmptyLabel'))
        return
    grid = QGridLayout()
    grid.setSpacing(10)
    for col in range(columns):
        grid.setColumnStretch(col, 1)
    for idx, item in enumerate(items):
        grid.addWidget(build_btn(item), idx // columns, idx % columns)
    container.addLayout(grid)


class WorldCircuitsDialog(StepPickerDialog):
    """Modal 3-step World Circuits picker (Continent -> Circuit -> Layout)."""

    def __init__(self, service: TuningService, parent: Optional[QWidget] = None) -> None:
        """Initialize the World Circuits dialog and populate Step 0 continents."""
        self._service = service
        self.selected_track_id: Optional[str] = None
        self._continent: Optional[str] = None
        super().__init__('World Circuits', 'World Circuits',
                         'Search tracks by name, circuit, country...', parent=parent)
        self._populate_continents()
        self._show_continents()

    def _populate_continents(self) -> None:
        """Build the 3 horizontal continent selector buttons for Step 0."""
        counts = self._service.world_circuit_continents()
        row = QHBoxLayout()
        row.setSpacing(12)
        for continent in TRACK_CONTINENTS:
            c_count, l_count = counts.get(continent, (0, 0))
            subtitle = f"{_plural(c_count, 'circuit', 'circuits')} · {_plural(l_count, 'layout', 'layouts')}"
            btn = make_picker_button(continent, subtitle, object_name='pickerContinentCard')
            btn.clicked.connect(lambda _=False, c=continent: self._show_circuits(c))
            row.addWidget(btn, 1)
        self.step_container(0).addLayout(row)

    def _show_continents(self) -> None:
        """Reset navigation state and display Step 0 (Continents)."""
        self._continent = None
        self.set_breadcrumbs([('World Circuits', self._show_continents)])
        self.show_step(0)

    def _make_circuit_button(self, continent: str, circuit: CircuitSummary) -> QPushButton:
        """Create a Step 1 circuit card button."""
        subtitle = f"{circuit.country} · {_plural(circuit.layout_count, 'layout', 'layouts')}"
        btn = make_picker_button(circuit.base_circuit, subtitle)
        btn.clicked.connect(lambda _=False, c=continent, bc=circuit.base_circuit: self._show_layouts(c, bc))
        return btn

    def _show_circuits(self, continent: str) -> None:
        """Populate and display Step 1 (Circuits) for `continent`."""
        self._continent = continent
        circuits = self._service.circuits_in_continent(continent)
        _populate_grid(self.step_container(1), circuits, _CIRCUIT_COLUMNS,
                       lambda circuit: self._make_circuit_button(continent, circuit), 'No circuits found')
        self.set_breadcrumbs([
            ('World Circuits', self._show_continents),
            (continent, lambda c=continent: self._show_circuits(c)),
        ])
        self.show_step(1)

    def _make_layout_button(self, track: TrackLayoutEntry) -> QPushButton:
        """Create a Step 2 / search track layout card button."""
        btn = make_picker_button(track.name, format_layout_subtitle(track))
        btn.clicked.connect(lambda _=False, tid=track.id: self._accept_track(tid))
        return btn

    def _show_layouts(self, continent: str, base_circuit: str) -> None:
        """Populate and display Step 2 (Layouts) for `base_circuit`."""
        self._continent = continent
        layouts = self._service.layouts_for_circuit(continent, base_circuit)
        _populate_grid(self.step_container(2), layouts, _LAYOUT_COLUMNS,
                       self._make_layout_button, 'No layouts found')
        self.set_breadcrumbs([
            ('World Circuits', self._show_continents),
            (continent, lambda c=continent: self._show_circuits(c)),
            (base_circuit, lambda c=continent, bc=base_circuit: self._show_layouts(c, bc)),
        ])
        self.show_step(2)

    def _accept_track(self, track_id: str) -> None:
        """Record chosen `track_id` and accept the dialog."""
        self.selected_track_id = track_id
        self.accept()

    def _on_back(self) -> None:
        """Navigate one step back while keeping breadcrumbs synchronized."""
        if self._active_step == 2 and self._continent:
            self._show_circuits(self._continent)
            return
        if self._active_step > 0:
            self._show_continents()

    def _on_search_changed(self, query: str) -> None:
        """Populate Step 3 search results for `query`."""
        tracks = self._service.search_catalog_tracks(query)
        _populate_grid(self.search_results_layout, tracks, _LAYOUT_COLUMNS,
                       self._make_layout_button, 'No matching tracks found')
