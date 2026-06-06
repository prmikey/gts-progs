from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .dates import format_warranty_date
from .model_names import normalize_model_name
from .models import WarrantyInfo


class LenovoLookupError(RuntimeError):
    pass


@dataclass
class LenovoWarrantyClient:
    country: str = "us"
    language: str = "en"
    timeout_seconds: int = 20
    model_map: dict[str, str] | None = None

    def lookup(self, serial: str, machine_type: str | None = None) -> WarrantyInfo:
        serial = serial.strip().upper()
        product_name = ""

        if not machine_type:
            product_name = self._get_product_name(serial)
            machine_type = self._parse_machine_type(product_name)

        if not machine_type:
            raise LenovoLookupError(f"{serial}: Lenovo did not return a machine type.")

        payload = {
            "serialNumber": serial,
            "machineType": machine_type,
            "country": self.country,
            "language": self.language,
        }
        response = self._request_json(
            "https://pcsupport.lenovo.com/us/en/api/v4/upsell/redport/getIbaseInfo",
            method="POST",
            payload=payload,
        )
        data = response.get("Data") or response.get("data") or {}
        warranty_end = self._extract_warranty_end(data)
        machine_info = data.get("machineInfo") or data.get("MachineInfo") or {}
        product = (
            machine_info.get("subSeries")
            or machine_info.get("SubSeries")
            or machine_info.get("productName")
            or machine_info.get("ProductName")
            or machine_info.get("product")
            or machine_info.get("Product")
            or product_name
        )

        return WarrantyInfo(
            serial=serial,
            warranty_end=format_warranty_date(warranty_end),
            model=normalize_model_name(product, self.model_map),
            machine_type=machine_type,
            subseries=str(product or ""),
            source="lenovo-live",
        )

    def _get_product_name(self, serial: str) -> str:
        url = f"https://pcsupport.lenovo.com/us/en/api/v4/mse/getproducts?productId={urllib.parse.quote(serial)}"
        response = self._request_json(url)
        name = self._find_first_key(response, "Name")
        if not name:
            name = self._find_first_key(response, "name")
        return "" if name is None else str(name)

    def _request_json(self, url: str, method: str = "GET", payload: dict[str, str] | None = None) -> dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/json",
        }
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                text = response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise LenovoLookupError(f"Lenovo request failed for {url}: {exc}") from exc
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LenovoLookupError(f"Lenovo returned non-JSON response for {url}.") from exc
        if not isinstance(parsed, dict):
            return {"items": parsed}
        return parsed

    @staticmethod
    def _parse_machine_type(product_name: str) -> str:
        match = re.search(r"\bType\s+([A-Z0-9]{4})\b", product_name or "", flags=re.IGNORECASE)
        return match.group(1).upper() if match else ""

    @classmethod
    def _find_first_key(cls, value: object, key: str) -> object:
        if isinstance(value, dict):
            if key in value:
                return value[key]
            for item in value.values():
                found = cls._find_first_key(item, key)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = cls._find_first_key(item, key)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _extract_warranty_end(data: dict) -> object:
        for key in ("currentWarranty", "upgradeWarranties", "contractWarranties", "baseWarranties"):
            warranties = data.get(key) or data.get(key[:1].upper() + key[1:]) or []
            if isinstance(warranties, dict):
                warranties = [warranties]
            end_dates = []
            for warranty in warranties:
                if not isinstance(warranty, dict):
                    continue
                end_dates.append(warranty.get("EndDate") or warranty.get("endDate") or warranty.get("end"))
            end_dates = [value for value in end_dates if value not in (None, "")]
            if end_dates:
                return max(end_dates)
        return data.get("EndDate") or data.get("endDate") or ""
