import json
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Dict


@dataclass(slots=True)
class PincodeData:
    circlename: str
    regionname: str
    divisionname: str
    officename: str
    pincode: str
    officetype: str
    delivery: str
    district: str
    statename: str
    latitude: float | None
    longitude: float | None

    @classmethod
    def from_dict(cls, data: dict) -> "PincodeData":
        lat = data.get("latitude")
        lon = data.get("longitude")

        return cls(
            **{
                **data,
                "latitude": None if lat in ("NA", "", None) else float(lat),
                "longitude": None if lon in ("NA", "", None) else float(lon),
            }
        )


class PinSearch:
    """
    Search and retrieve Indian postal information using PIN codes,
    state names, and district names.

    PARAMETERS:
    pincode_file : Path | None, optional
        Path to the pincode data file. If not provided, the default
        data file included with the package will be used.

    Examples
    --------
    Create a client:

    >>> pins = PinSearch()

    Lookup a specific PIN code:

    >>> record = pins.get("504273")
    >>> record.officename
    'Karjibheempur B.O'

    Search by state:

    >>> for office in pins.by_state("TELANGANA"):
    ...     print(office.pincode)

    Search by district:

    >>> for office in pins.by_district("MANCHERIAL"):
    ...     print(office.officename)

    Iterate over the entire dataset:

    >>> for office in pins:
    ...     print(office.pincode)

    Get the total number of records:

    >>> len(pins)

    Attributes
    ----------
    _DATA_FILE : pathlib.Path
        Path to the dataset file.

    _state_index : collections.defaultdict[list]
        Internal state-based lookup index.

    _district_index : collections.defaultdict[list]
        Internal district-based lookup index.
    """

    def __init__(self, pincode_file: Path | None = None):
        if pincode_file is not None:
            self._DATA_FILE = pincode_file
        else:
            self._DATA_FILE = files("pinsearch_sdk").joinpath("pincode_data.json")

        # Build indexes
        self._state_index = defaultdict(list)
        self._district_index = defaultdict(list)
        self._build_indexes()

    def __iter__(self) -> Iterator[PincodeData]:
        for record in self._read_pincode_data().values():
            yield PincodeData.from_dict(record)

    def __len__(self) -> int:
        return len(self._read_pincode_data())

    @lru_cache(maxsize=1)
    def _read_pincode_data(self) -> Dict:
        with self._DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _build_indexes(self) -> None:
        data = self._read_pincode_data()

        for record in data.values():
            self._state_index[record["statename"].upper()].append(record)

            self._district_index[record["district"].upper()].append(record)

    def get(self, pincode: str | int) -> PincodeData | None:
        """search using a pincode\n
        Example:
                >>> PinSearch().get("000000")
        """
        data = self._read_pincode_data()
        record = data.get(str(pincode))

        if record is None:
            return None

        return PincodeData.from_dict(record)

    def by_state(self, state_name: str) -> Iterator[PincodeData]:
        """search using a state name\n
        Example:
                >>> PinSearch().by_state("delhi")
        """
        for record in self._state_index[state_name.upper()]:
            yield PincodeData.from_dict(record)

    def by_district(self, district: str) -> Iterator[PincodeData]:
        """search using a district\n
        Example:
                >>> PinSearch().by_district("delhi")
        """
        for record in self._district_index[district.upper()]:
            yield PincodeData.from_dict(record)
