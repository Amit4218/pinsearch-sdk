# pinsearch-sdk

A lightweight Python SDK for searching Indian Postal Index Number (PIN) code data.

`pinsearch-sdk` provides fast offline access to Indian postal information, including:

* PIN code lookups
* State-based searches
* District-based searches
* Office information
* Geographic coordinates (when available)

The SDK ships with a pre-indexed dataset and requires no external API or internet connection.

---

## Installation

```bash
pip install pinsearch-sdk
```

or with uv:

```bash
uv add pinsearch-sdk
```

---

## Quick Start

```python
from pinsearch_sdk import PinSearch

client = PinSearch()

record = client.get("504273")

print(record.officename)
print(record.district)
print(record.statename)
```

Output:

```text
Karjibheempur B.O
MANCHERIAL
TELANGANA
```

---

## Lookup by PIN Code

```python
from pinsearch_sdk import PinSearch

client = PinSearch()

record = client.get("504273")

print(record)
```

Returns:

```python
PincodeData(
    circlename='Telangana Circle',
    regionname='Hyderabad Region',
    divisionname='Adilabad Division',
    officename='Karjibheempur B.O',
    pincode='504273',
    officetype='BO',
    delivery='Delivery',
    district='MANCHERIAL',
    statename='TELANGANA',
    latitude=19.335427,
    longitude=79.4928856
)
```

If the PIN code does not exist:

```python
record = client.get("000000")

print(record)
```

```text
None
```

---

## Search by State

```python
from pinsearch_sdk import PinSearch

client = PinSearch()

for office in client.by_state("TELANGANA"):
    print(office.officename)
```

The method returns an iterator and yields `PincodeData` objects lazily.

Convert to a list if needed:

```python
results = list(client.by_state("TELANGANA"))
```

---

## Search by District

```python
from pinsearch_sdk import PinSearch

client = PinSearch()

for office in client.by_district("MANCHERIAL"):
    print(office.pincode)
```

---

## Iterate Over the Entire Dataset

```python
from pinsearch_sdk import PinSearch

client = PinSearch()

for office in client:
    print(office.pincode)
```

---

## Data Model

Every search method returns a `PincodeData` object.

```python
@dataclass
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
```

---

## Example

```python
from pinsearch_sdk import PinSearch

client = PinSearch()

record = client.get("504273")

print(record.officename)
print(record.latitude)
print(record.longitude)
```

Output:

```text
Karjibheempur B.O
19.335427
79.4928856
```

---

## Performance

* PIN code lookups are O(1)
* State searches use pre-built indexes
* District searches use pre-built indexes
* Search results are yielded lazily to reduce memory usage

---

## Data Source

The information is derived from publicly available dataset from [Open Government Data (OGD) Platform India](https://www.data.gov.in)
The data is intended for informational purposes and may not always reflect the latest changes made by India Post.

---

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
