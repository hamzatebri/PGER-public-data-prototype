from __future__ import annotations

import csv
import hashlib
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "boe_procurement" / "licitaciones_contrataciones_BOE_2014_2024.csv"
OUT_DIR = ROOT / "data" / "processed"
OUT = OUT_DIR / "public_procurement_exposure_2022_2024.csv"
PROFILE = OUT_DIR / "portfolio_profile.txt"
AUDIT = OUT_DIR / "portfolio_cleaning_audit.csv"
EXPECTED_SOURCE_SHA256 = "d40c6d8318075b48a6aeba376a1b7300f5ac363aaeb8d314534bdd4918b5256e"


# CPV divisions from the Common Procurement Vocabulary. The first two digits
# identify the division, so every source row can be assigned without a broad
# residual "Other" category.
CPV_DIVISIONS = {
    "03": "Agricultural, farming, fishing and forestry products",
    "09": "Petroleum, fuel, electricity and other energy sources",
    "14": "Mining, basic metals and related products",
    "15": "Food, beverages, tobacco and related products",
    "16": "Agricultural machinery",
    "18": "Clothing, footwear, luggage and accessories",
    "19": "Leather, textiles, plastic and rubber materials",
    "22": "Printed matter and related products",
    "24": "Chemical products",
    "30": "Office and computing equipment and supplies",
    "31": "Electrical machinery, equipment and consumables",
    "32": "Communication and telecommunications equipment",
    "33": "Medical equipment, pharmaceuticals and personal care products",
    "34": "Transport equipment and auxiliary products",
    "35": "Security, fire-fighting, police and defence equipment",
    "37": "Musical instruments, sports goods, games and toys",
    "38": "Laboratory, optical and precision equipment",
    "39": "Furniture, domestic appliances and cleaning products",
    "41": "Collected and purified water",
    "42": "Industrial machinery",
    "43": "Mining, quarrying and construction machinery",
    "44": "Construction structures and materials",
    "45": "Construction work",
    "48": "Software packages and information systems",
    "50": "Repair and maintenance services",
    "51": "Installation services",
    "55": "Hotel, restaurant and retail services",
    "60": "Transport services",
    "63": "Supporting and auxiliary transport services",
    "64": "Postal and telecommunications services",
    "65": "Public utilities",
    "66": "Financial and insurance services",
    "70": "Real-estate services",
    "71": "Architecture, construction, engineering and inspection services",
    "72": "IT services",
    "73": "Research and development services",
    "75": "Administration, defence and social security services",
    "76": "Services related to the oil and gas industry",
    "77": "Agricultural, forestry and related services",
    "79": "Business services",
    "80": "Education and training services",
    "85": "Health and social work services",
    "90": "Sewage, refuse, cleaning and environmental services",
    "92": "Recreational, cultural and sporting services",
    "98": "Other community, social and personal services",
}


def parse_euro(value: str) -> float | None:
    text = (value or "").lower().replace("euros", "").replace("€", "").strip()
    text = text.replace(".", "").replace(",", ".")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def first_cpv_code(value: str) -> str:
    match = re.search(r"\b(\d{8})\b", value or "")
    return match.group(1) if match else ""


def cpv_group(code: str) -> str:
    prefix = code[:2]
    if prefix not in CPV_DIVISIONS:
        raise ValueError(f"Unmapped CPV division: {prefix or '<missing>'}")
    return CPV_DIVISIONS[prefix]


def normalise_entity_name(value: str) -> str:
    """Merge case, accent, punctuation and spacing variants.

    The original published name remains in ``awardee_name_source``.  This key
    is used only to group formatting variants such as ``S.L.`` and ``SL`` for
    concentration calculations and anonymous display identifiers.
    """
    text = unicodedata.normalize("NFKD", value)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.upper().replace("&", " Y ")
    return re.sub(r"[^A-Z0-9]+", "", text)


def source_notice_id(url: str) -> str:
    match = re.search(r"[?&]id=([^&]+)", url or "")
    return match.group(1) if match else (url or "").strip()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if source_digest != EXPECTED_SOURCE_SHA256:
        raise ValueError(
            "The raw BOE file does not match Zenodo record 18712463 in the source register."
        )
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    eligible_rows: list[dict[str, str]] = []
    for source_row in source_rows:
        year = source_row["Fecha"][-4:]
        awardee = source_row["nombre_adjudicatario"].strip()
        awarded_value = parse_euro(source_row["valor_oferta_adjudicada"])
        # Contracting notices provide the observed awardee and awarded value. Tender
        # notices are excluded because they may not represent an awarded relationship.
        if (
            source_row["Tipo"].strip() != "Contratación"
            or year not in {"2022", "2023", "2024"}
            or not awardee
            or awardee.lower() == "no disponible"
            or awarded_value is None
        ):
            continue
        cpv_code = first_cpv_code(source_row["Codigos_CPV"])
        if not cpv_code:
            cpv_code = first_cpv_code(source_row["Materias_CPV"])
        eligible_rows.append(
            {
                "contract_id": source_row["Expediente"],
                "notice_type": source_row["Tipo"],
                "contracting_authority_name": source_row["Institucion"],
                "responsible_body": source_row["Organismo responsable"],
                "contracting_authority_region": source_row["Ambito_geografico"],
                "awardee_name_source": awardee,
                "publication_date": datetime.strptime(source_row["Fecha"], "%d/%m/%Y").date().isoformat(),
                "contract_value_eur": f"{awarded_value:.2f}",
                "cpv_code": cpv_code,
                "cpv_description": source_row["Materias_CPV"],
                "sector_group": "",
                "contract_type": source_row["Naturaleza"],
                "procurement_procedure": source_row["Procedimiento"],
                "object_description": source_row["Objeto"],
                "source_url": source_row["Enlace HTML"],
            }
        )

    # In this frozen release every repeated source URL occurs exactly twice.
    # Inspection of all repeated pairs showed that the first row is the award
    # record and the second is an appeals body, contracting office or registry
    # captured by the source parser. One row per source URL removes that parser
    # artefact while preserving every distinct published BOE notice.
    url_counts = Counter(row["source_url"] for row in eligible_rows)
    repeated_sizes = {count for count in url_counts.values() if count > 1}
    if repeated_sizes != {2}:
        raise ValueError(f"Unexpected repeated source-URL group sizes: {sorted(repeated_sizes)}")
    rows: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for source_row in eligible_rows:
        url = source_row["source_url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        entity_key = normalise_entity_name(source_row["awardee_name_source"])
        rows.append(
            {
                "exposure_id": f"BOE-{len(rows) + 1:05d}",
                "source_notice_id": source_notice_id(url),
                **source_row,
                "awardee_entity_key": entity_key,
            }
        )

    for row in rows:
        row["sector_group"] = cpv_group(str(row["cpv_code"]))

    awardee_counts = Counter(str(row["awardee_entity_key"]) for row in rows)
    awardee_ids = {name: f"A{index:04d}" for index, name in enumerate(sorted(awardee_counts), start=1)}
    total_value = sum(float(row["contract_value_eur"]) for row in rows)
    awardee_value = defaultdict(float)
    authority_value = defaultdict(float)
    authority_awardee_value = defaultdict(float)
    authority_notice_count = Counter()
    authority_awardee_notice_count = Counter()
    sector_value = defaultdict(float)
    for row in rows:
        value = float(row["contract_value_eur"])
        awardee = str(row["awardee_entity_key"])
        authority = str(row["contracting_authority_name"])
        sector = str(row["sector_group"])
        awardee_value[awardee] += value
        authority_value[authority] += value
        authority_awardee_value[(authority, awardee)] += value
        authority_notice_count[authority] += 1
        authority_awardee_notice_count[(authority, awardee)] += 1
        sector_value[sector] += value
    for row in rows:
        name = str(row["awardee_entity_key"])
        value = float(row["contract_value_eur"])
        authority = str(row["contracting_authority_name"])
        sector = str(row["sector_group"])
        row["awardee_display_id"] = awardee_ids[name]
        row["awardee_contract_count"] = str(awardee_counts[name])
        row["awardee_portfolio_value_share"] = f"{awardee_value[name] / total_value:.8f}" if total_value else "0"
        row["authority_awardee_value_share"] = f"{authority_awardee_value[(authority, name)] / authority_value[authority]:.8f}" if authority_value[authority] else "0"
        row["authority_awardee_notice_share"] = f"{authority_awardee_notice_count[(authority, name)] / authority_notice_count[authority]:.8f}" if authority_notice_count[authority] else "0"
        row["sector_portfolio_value_share"] = f"{sector_value[sector] / total_value:.8f}" if total_value else "0"
        row["data_quality_flags"] = "unique_source_notice;named_awardee;parsed_awarded_value;case_accent_punctuation_spacing_normalised;source_url_available"

    fieldnames = list(rows[0]) if rows else []
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    duplicate_rows_removed = len(eligible_rows) - len(rows)
    with AUDIT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["check", "observed_value", "decision"])
        writer.writerow(["eligible_rows_before_notice_deduplication", len(eligible_rows), "profiled"])
        writer.writerow(["repeated_source_url_groups", sum(count > 1 for count in url_counts.values()), "one first award row retained per URL"])
        writer.writerow(["duplicate_parser_rows_removed", duplicate_rows_removed, "removed"])
        writer.writerow(["unique_source_urls_after_cleaning", len(seen_urls), "required unique"])
        writer.writerow(["normalised_awardee_entities", len(awardee_ids), "used for concentration and display IDs"])
    profile = [
        "PGER public-procurement exposure portfolio",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "Scope: BOE records dated 2022-01-01 through 2024-12-31",
        "Eligibility: Tipo=Contratación, 2022-2024, named awardee, parseable awarded value, one first award record per source URL",
        f"Eligible rows before source-parser duplicate removal: {len(eligible_rows)}",
        f"Source-parser duplicate rows removed: {duplicate_rows_removed}",
        f"Published notice records: {len(rows)}",
        f"Distinct procurement references: {len({str(row['contract_id']) for row in rows})}",
        f"Normalised awardee entities: {len(awardee_ids)}",
        f"Total published notice value EUR: {total_value:.2f}",
        f"Output SHA-256: {digest}",
        f"Raw source SHA-256: {source_digest}",
        "Interpretation: each row is one published BOE source notice with a named awardee and awarded value.",
        "Case, accent, punctuation and spacing variants share one grouping key; the original awardee name remains available for traceability.",
    ]
    PROFILE.write_text("\n".join(profile) + "\n", encoding="utf-8")
    print("Built", OUT)
    print("Published notice records:", len(rows), "Normalised awardee entities:", len(awardee_ids))
    print("Source-parser duplicate rows removed:", duplicate_rows_removed, "SHA256:", digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
