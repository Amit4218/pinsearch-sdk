from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any

import ddddocr
import requests


class ScraperError(Exception):
    """Base scraper exception."""


class CaptchaDownloadError(ScraperError):
    pass


class CaptchaSolveError(ScraperError):
    pass


class DownloadRequestError(ScraperError):
    pass


class CSVProcessingError(ScraperError):
    pass


class DataFileScraper:
    REQUEST_TIMEOUT = 60

    def __init__(
        self,
        logger: logging.Logger,
        base_url: str,
        resource_url: str,
        resource_origin: str,
        resource_id: str,
        file_download_dir: str = "src/pinsearch_sdk",
        pincode_file_name: str = "src/pinsearch_sdk/pincode_data.json",
    ) -> None:

        self.logger = logger
        self.base_url = base_url
        self.resource_url = resource_url
        self.resource_origin = resource_origin
        self.resource_id = resource_id
        self.download_dir = Path(file_download_dir)
        self.output_json = Path(pincode_file_name)
        self.session = requests.Session()
        self.captcha_sid: str | None = None
        self.captcha_token: str | None = None
        self._add_headers()

    def _add_headers(self) -> None:
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/148.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": self.resource_origin,
                "Referer": self.resource_url,
            }
        )

    def _get_json(self, url: str) -> dict[str, Any]:
        """get the JSON response from the given URL"""
        try:
            response = self.session.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            self.logger.exception("GET request failed: %s", url)
            raise ScraperError(f"Failed GET request: {url}") from exc

    def _download_file(self, url: str, destination: Path) -> Path:
        """download the file from the given URL and save it to the destination path"""
        try:
            response = self.session.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
                allow_redirects=True,
                stream=True,
            )

            response.raise_for_status()

            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            return destination

        except requests.RequestException as exc:
            self.logger.exception("File download failed. url=%s", url)
            raise ScraperError("File download failed") from exc

    def download_captcha(self) -> Path:
        """download the captcha image and return the path to the downloaded file"""
        self.logger.info("Downloading captcha")
        try:
            data = self._get_json(self.base_url)
            self.captcha_sid = data["sid"]
            self.captcha_token = data["token"]

            image_base_url = self.base_url.split("v1/")[0]
            image_url = f"{image_base_url}v1{data['url']}"
            captcha_file = self.download_dir / "captcha.png"

            self._download_file(image_url, captcha_file)
            self.logger.info("Captcha downloaded successfully")
            return captcha_file

        except KeyError as exc:
            self.logger.exception("Invalid captcha response payload")
            raise CaptchaDownloadError("Captcha metadata missing") from exc

    def solve_captcha(self, image_path: Path) -> str:
        """solve the captcha using the given image path and return the captcha text"""
        self.logger.info("Starting captcha OCR")
        try:
            ocr = ddddocr.DdddOcr()
            result = ocr.classification(image_path.read_bytes())

            if not result:
                raise ValueError("OCR returned empty result")

            result = str(result).upper()
            self.logger.info("Captcha solved successfully")
            return result

        except Exception as exc:
            self.logger.exception("Captcha OCR failed")
            raise CaptchaSolveError("Failed solving captcha") from exc
        finally:
            image_path.unlink(missing_ok=True)

    def request_download_url(self, captcha_text: str) -> str:
        """request the download URL using the given captcha text and return the URL"""
        if not self.captcha_sid:
            raise DownloadRequestError("Captcha SID missing")

        if not self.captcha_token:
            raise DownloadRequestError("Captcha token missing")

        payload = {
            "name": [{"value": "Resource Download"}],
            "field_domain": ["4"],
            "field_domain_visibility": ["4", "4"],
            "catalog_id": [{"target_id": ""}],
            "export_status": [{"value": "download"}],
            "file_type": [{"value": "csv"}],
            "ip": [{"value": ""}],
            "ogdp_captcha_response": [{"value": captcha_text}],
            "ogdp_captcha_sid": [{"value": self.captcha_sid}],
            "ogdp_captcha_token": [{"value": self.captcha_token}],
            "parameters": {},
            "purpose": [{"value": "3"}],
            "resource_id": [{"target_id": self.resource_id}],
            "uid": [{"value": 0}],
            "usage": [{"value": "2"}],
        }

        request_url = self.base_url.replace("captcha/refresh/image/", "")

        try:
            response = self.session.post(
                request_url, json=payload, timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            download_url = data["download_url"]
            self.logger.info("Download URL received")
            return download_url

        except requests.RequestException as exc:
            self.logger.exception("Download URL request failed")
            raise DownloadRequestError("Failed requesting download URL") from exc

        except KeyError as exc:
            self.logger.exception("download_url missing from response")
            raise DownloadRequestError("Invalid API response") from exc

    def download_csv(self, download_url: str) -> Path:
        """download the CSV file from the given URL and save it to the download directory"""
        csv_path = self.download_dir / "datafile.csv"
        self.logger.info("Downloading CSV file")
        return self._download_file(download_url, csv_path)

    def read_csv_data(self, csv_file: Path) -> dict[str, dict[str, Any]]:
        """read the CSV file and return the data as a dictionary"""
        self.logger.info("Reading CSV file %s", csv_file)
        result: dict[str, dict[str, Any]] = {}

        try:
            with csv_file.open(encoding="utf-8", newline="") as file:
                reader = csv.reader(file)

                for row_num, row in enumerate(reader, start=2):
                    try:
                        result[row[4]] = {
                            "circlename": row[0],
                            "regionname": row[1],
                            "divisionname": row[2],
                            "officename": row[3],
                            "pincode": row[4],
                            "officetype": row[5],
                            "delivery": row[6],
                            "district": row[7],
                            "statename": row[8],
                            "latitude": (
                                float(row[9]) if type(row[9]) is float else None
                            ),
                            "longitude": (
                                float(row[10]) if type(row[10]) is float else None
                            ),
                        }

                    except ValueError:
                        self.logger.warning(
                            "Skipping row %s due to invalid coordinates", row_num
                        )

            self.logger.info(
                "Processed %s pincodes",
                len(result),
            )
            return result

        except Exception as exc:
            self.logger.exception("Failed processing CSV")
            raise CSVProcessingError("CSV processing failed") from exc
        finally:
            csv_file.unlink(missing_ok=True)

    def write_json(self, data: dict[str, Any]) -> None:
        """write the given data to the output JSON file"""

        try:
            self.output_json.parent.mkdir(parents=True, exist_ok=True)
            with self.output_json.open(
                "w",
                encoding="utf-8",
            ) as fp:
                json.dump(data, fp, indent=4, ensure_ascii=False)

            self.logger.info(
                "Successfully wrote %s records to %s", len(data), self.output_json
            )

        except OSError:
            self.logger.exception("Failed writing JSON")
            raise

    def start(self) -> None:
        self.logger.info("Starting scraper for resource=%s", self.resource_id)
        try:
            captcha_image = self.download_captcha()
            captcha_text = self.solve_captcha(captcha_image)
            download_url = self.request_download_url(captcha_text)
            csv_file = self.download_csv(download_url)
            data = self.read_csv_data(csv_file)
            self.write_json(data)
            self.logger.info("Scraper completed successfully")

        except ScraperError:
            self.logger.exception("Scraper failed")
            raise

        except Exception:
            self.logger.exception("Unexpected error")
            raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    scraper = DataFileScraper(
        base_url=sys.argv[1],
        resource_url=sys.argv[2],
        resource_origin=sys.argv[3],
        resource_id=sys.argv[4],
        logger=logging.getLogger(__name__),
    )
    scraper.start()
