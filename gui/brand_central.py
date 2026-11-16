"""Brand Central 3-step car picker dialog (Continent -> Country/Brand -> Car)."""
from typing import Optional, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from db.catalog import CAR_CONTINENTS, CarEntry, CountryBrands
from gui.picker_dialog import StepPickerDialog, clear_layout, make_picker_button
from gui.service import TuningService

_COLUMNS = 3
_COUNTRY_COL_WIDTH = 120


def _plural(count: int, word: str) -> str:
    """Return `count word` with English pluralization."""
    return f'{count} {word}' if count == 1 else f'{count} {word}s'


def _make_grid(columns: int) -> QGridLayout:
    """Create an evenly stretched `columns`-column grid layout."""
    grid = QGridLayout()
    grid.setSpacing(8)
    for col in range(columns):
        grid.setColumnStretch(col, 1)
    return grid


def format_car_subtitle(car: CarEntry) -> str:
    """Build concise car card subtitle, omitting missing telemetry such as PP."""
    parts = [p for p in (car.group, car.drivetrain) if p]
    if car.power_hp is not None:
        parts.append(f'{car.power_hp} hp')
    if car.mass_kg is not None:
        parts.append(f'{car.mass_kg} kg')
    if car.stock_pp is not None:
        parts.append(f'PP {car.stock_pp:.2f}')
    return ' · '.join(parts)


class BrandCentralDialog(StepPickerDialog):
    """Modal step-by-step Brand Central car selector."""

    def __init__(self, service: TuningService, parent: Optional[QWidget] = None) -> None:
        self._service = service
        self._selected_continent: Optional[str] = None
        self.selected_car_id: Optional[str] = None
        super().__init__(
            'Brand Central',
            'Brand Central',
            'Search cars by name, brand, country, or ID...',
            parent,
        )
        self._populate_continents()
        self._show_continents()

    def _populate_continents(self) -> None:
        """Render the three Brand Central continent buttons on step 0."""
        container = self.step_container(0)
        clear_layout(container)
        counts = self._service.brand_central_continents()
        row = QHBoxLayout()
        row.setSpacing(12)
        for continent in CAR_CONTINENTS:
            brands_n, cars_n = counts.get(continent, (0, 0))
            subtitle = f"{_plural(brands_n, 'brand')} · {_plural(cars_n, 'car')}"
            btn = make_picker_button(continent, subtitle, object_name='pickerContinentCard')
            btn.clicked.connect(lambda _=False, cont=continent: self._show_brands(cont))
            row.addWidget(btn, 1)
        container.addLayout(row)

    def _show_continents(self) -> None:
        """Switch to step 0 and reset breadcrumbs to Brand Central root."""
        self._selected_continent = None
        self.set_breadcrumbs([('Brand Central', self._show_continents)])
        self.show_step(0)

    def _show_brands(self, continent: str) -> None:
        """Populate step 1 with country-grouped brands for `continent`."""
        self._selected_continent = continent
        container = self.step_container(1)
        clear_layout(container)
        for group in self._service.brands_by_country(continent):
            container.addLayout(self._build_country_row(continent, group))
        self.set_breadcrumbs([
            ('Brand Central', self._show_continents),
            (continent, lambda c=continent: self._show_brands(c)),
        ])
        self.show_step(1)

    def _build_country_row(self, continent: str, group: CountryBrands) -> QHBoxLayout:
        """Build one horizontal row with country label on left and 3-col brand grid."""
        row = QHBoxLayout()
        row.setSpacing(12)
        label = QLabel(group.country, objectName='pickerCountryLabel', wordWrap=True)
        label.setFixedWidth(_COUNTRY_COL_WIDTH)
        label.setContentsMargins(0, 8, 0, 0)
        row.addWidget(label, 0, Qt.AlignmentFlag.AlignTop)
        grid = _make_grid(_COLUMNS)
        for idx, brand in enumerate(group.brands):
            btn = make_picker_button(f'{brand.name} ({brand.car_count})')
            btn.clicked.connect(lambda _=False, c=continent, b=brand.name: self._show_cars(c, b))
            grid.addWidget(btn, idx // _COLUMNS, idx % _COLUMNS)
        row.addLayout(grid, 1)
        return row

    def _show_cars(self, continent: str, brand: str) -> None:
        """Populate step 2 with cars belonging to `brand` in `continent`."""
        self._selected_continent = continent
        container = self.step_container(2)
        clear_layout(container)
        self._populate_car_grid(container, self._service.cars_in_brand(continent, brand))
        self.set_breadcrumbs([
            ('Brand Central', self._show_continents),
            (continent, lambda c=continent: self._show_brands(c)),
            (brand, lambda c=continent, b=brand: self._show_cars(c, b)),
        ])
        self.show_step(2)

    def _populate_car_grid(self, target: QVBoxLayout, cars: Sequence[CarEntry]) -> None:
        """Render a 3-column grid of clickable car cards into `target`."""
        grid = _make_grid(_COLUMNS)
        for idx, car in enumerate(cars):
            btn = make_picker_button(car.short_name, format_car_subtitle(car))
            btn.clicked.connect(lambda _=False, cid=car.id: self._accept_car(cid))
            grid.addWidget(btn, idx // _COLUMNS, idx % _COLUMNS)
        target.addLayout(grid)

    def _accept_car(self, car_id: str) -> None:
        """Record chosen `car_id` and accept the modal dialog."""
        self.selected_car_id = car_id
        self.accept()

    def _on_back(self) -> None:
        """Step back from cars -> brands -> continents and refresh breadcrumbs."""
        if self._active_step == 2 and self._selected_continent is not None:
            self._show_brands(self._selected_continent)
            return
        if self._active_step == 1:
            self._show_continents()

    def _on_search_changed(self, query: str) -> None:
        """Render matching car cards or empty-state label for `query`."""
        clear_layout(self.search_results_layout)
        cars = self._service.search_catalog_cars(query)
        if not cars:
            self.search_results_layout.addWidget(
                QLabel('No matching cars found', objectName='pickerEmptyLabel')
            )
            return
        self._populate_car_grid(self.search_results_layout, cars)
