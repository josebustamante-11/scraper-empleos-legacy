"""
parser.py — Extrae y normaliza convocatorias de empleo desde HTML.

Soporta dos escenarios comunes:
1. Listados con tarjetas article
2. Páginas detalle con ld+json tipo JobPosting

El objetivo es devolver una estructura estándar que sirva para empleo
estatal o privado, manteniendo además los campos mínimos usados por el
resto del proyecto.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger


ITEM_SELECTOR = "article"


STANDARD_JOB_TEMPLATE = {
    "schema_version": "1.0",
    "id": "",
    "source": {
        "site": "",
        "page_type": "",
        "url": "",
        "canonical_url": "",
        "detail_url": "",
        "apply_url": "",
    },
    "job": {
        "title": "",
        "slug": "",
        "summary": "",
        "description": "",
        "employment_type": "",
        "workplace_type": "",
        "category": "",
        "vacancies": None,
        "salary": {
            "raw": "",
            "currency": "",
            "min": None,
            "max": None,
            "period": "",
        },
    },
    "organization": {
        "name": "",
        "logo_url": "",
        "sector": "",
    },
    "location": {
        "raw": "",
        "district": "",
        "city": "",
        "region": "",
        "country": "",
    },
    "dates": {
        "published_at": "",
        "deadline": "",
        "application_window": "",
    },
    "profile": {
        "target_audience": "",
        "academic_requirements": "",
        "experience": [],
        "courses": [],
        "knowledge": [],
    },
    "application": {
        "instructions": "",
        "schedule": "",
        "documents": [],
        "bases_url": "",
        "position_profile_url": "",
        "annex_urls": [],
    },
    "attachments": [],
    "sections": {
        "overview": "",
        "requirements": "",
        "contract_conditions": "",
        "how_to_apply": "",
        "bases": "",
        "position_profile": "",
    },
    "raw": {
        "json_ld": {},
        "visible_sections": {},
    },
}


def parse_items(
    html: str,
    base_url: str | None = None,
) -> list[dict]:
    """
    Parsea el HTML y retorna items con una estructura estándar.

    Mantiene compatibilidad con el flujo existente devolviendo además los
    campos top-level: title, slug, content, url, image y date.
    """
    soup = BeautifulSoup(html, "lxml")
    json_ld = _extract_job_posting_json_ld(soup)
    canonical_url = _get_canonical_url(soup, base_url)

    items = _parse_listing_items(
        soup,
        base_url,
    )
    if items:
        logger.info(f"Encontrados {len(items)} elementos con selector '{ITEM_SELECTOR}'")
        return items

    detail_item = _parse_detail_page(soup, json_ld, base_url, canonical_url)
    if detail_item:
        logger.info("Detectada página detalle. Se extrajo 1 convocatoria.")
        return [detail_item]

    logger.warning(
        "No se pudieron extraer convocatorias. Revisá si el HTML corresponde "
        "a un listado con 'article' o a una página detalle con contenido visible/JSON-LD."
    )
    return []


def enrich_item_with_detail(
    item: dict,
    detail_fetcher: Callable[[str], str | None],
    base_url: str | None = None,
) -> dict:
    """Complementa un item listado con datos de su página detalle."""
    return _enrich_listing_item_from_detail(item, base_url, detail_fetcher)


def _parse_listing_items(
    soup: BeautifulSoup,
    base_url: str | None,
) -> list[dict]:
    items = []
    for el in soup.select(ITEM_SELECTOR):
        item = _extract_listing_item(el, base_url)
        if item:
            items.append(item)
    return items


def _extract_listing_item(el: Tag, base_url: str | None) -> dict | None:
    title_link = _find_best_detail_link(el)
    title = clean_text(title_link.get_text(" ", strip=True)) if title_link else ""
    if not title:
        title_el = el.select_one("h1, h2, h3, h4")
        title = clean_text(title_el.get_text(" ", strip=True)) if title_el else ""
    if not title:
        return None

    detail_url = _normalize_url(title_link.get("href") if title_link else "", base_url)
    image_el = el.select_one("img")
    image_url = _normalize_url(_get_image_src(image_el), base_url)
    entity = _extract_labeled_text(el, "Entidad")
    profile = _extract_labeled_text(el, "Dirigido a")
    location_raw = _extract_location_from_listing(el)
    salary_raw = _extract_salary_from_listing(el)
    deadline = _extract_deadline_from_listing(el)

    standard = _new_standard_item()
    standard["source"]["page_type"] = "listing"
    standard["source"]["detail_url"] = detail_url
    standard["source"]["url"] = detail_url
    standard["source"]["canonical_url"] = detail_url
    standard["job"]["title"] = title
    standard["job"]["slug"] = _extract_slug_from_url(detail_url) or slugify(title)
    standard["job"]["summary"] = profile
    standard["job"]["description"] = profile
    standard["organization"]["name"] = entity
    standard["organization"]["logo_url"] = image_url
    standard["location"].update(_split_location(location_raw))
    standard["location"]["raw"] = location_raw
    standard["dates"]["deadline"] = deadline
    standard["profile"]["target_audience"] = profile

    if salary_raw:
        standard["job"]["salary"] = _build_salary_dict(salary_raw)

    return _finalize_item(standard)


def _parse_detail_page(
    soup: BeautifulSoup,
    json_ld: dict,
    base_url: str | None,
    canonical_url: str,
) -> dict | None:
    title = _extract_detail_title(soup, json_ld)
    if not title:
        return None

    standard = _new_standard_item()
    standard["source"]["page_type"] = "detail"
    standard["source"]["site"] = _extract_site_name(soup)
    standard["source"]["url"] = canonical_url
    standard["source"]["canonical_url"] = canonical_url
    standard["source"]["detail_url"] = canonical_url
    standard["source"]["apply_url"] = _extract_apply_url(soup, base_url)
    standard["job"]["title"] = title
    standard["job"]["slug"] = _extract_slug_from_url(canonical_url) or slugify(title)

    if json_ld:
        _hydrate_from_json_ld(standard, json_ld, base_url, canonical_url)

    _hydrate_from_detail_html(standard, soup, base_url)
    return _finalize_item(standard)


def _new_standard_item() -> dict:
    return deepcopy(STANDARD_JOB_TEMPLATE)


def _finalize_item(standard: dict) -> dict:
    title = clean_text(standard["job"].get("title", ""))
    detail_url = standard["source"].get("detail_url") or standard["source"].get("url", "")
    slug = _extract_slug_from_url(detail_url) or slugify(title)
    summary = clean_text(standard["job"].get("summary", ""))
    description = clean_text(standard["job"].get("description", ""))
    content = description or summary
    image_url = standard["organization"].get("logo_url", "")
    date = standard["dates"].get("deadline") or standard["dates"].get("published_at", "")

    standard["job"]["title"] = title
    standard["job"]["slug"] = slug
    standard["job"]["summary"] = summary
    standard["job"]["description"] = content

    return {
        "title": title,
        "slug": slug,
        "content": content,
        "url": detail_url,
        "image": image_url,
        "date": date,
        "standardized": standard,
    }


def _hydrate_from_json_ld(
    standard: dict,
    job_posting: dict,
    base_url: str | None,
    canonical_url: str,
) -> None:
    standard["raw"]["json_ld"] = job_posting
    standard["job"]["title"] = clean_text(job_posting.get("title", standard["job"]["title"]))
    standard["job"]["summary"] = clean_text(job_posting.get("description", ""))
    standard["job"]["description"] = clean_text(job_posting.get("description", ""))
    standard["job"]["employment_type"] = clean_text(job_posting.get("employmentType", ""))
    standard["dates"]["published_at"] = clean_text(job_posting.get("datePosted", ""))
    standard["dates"]["deadline"] = clean_text(job_posting.get("validThrough", ""))

    organization = job_posting.get("hiringOrganization") or {}
    if isinstance(organization, dict):
        standard["organization"]["name"] = clean_text(organization.get("name", ""))
        standard["organization"]["logo_url"] = _normalize_url(organization.get("logo", ""), base_url)

    address = (((job_posting.get("jobLocation") or {}).get("address")) or {})
    if isinstance(address, dict):
        locality = clean_text(address.get("addressLocality", ""))
        region = clean_text(address.get("addressRegion", ""))
        country = clean_text(address.get("addressCountry", ""))
        standard["location"]["district"] = locality
        standard["location"]["city"] = locality
        standard["location"]["region"] = region
        standard["location"]["country"] = country
        standard["location"]["raw"] = clean_text(
            ", ".join(part for part in [locality, region, country] if part)
        )

    salary_info = job_posting.get("baseSalary") or {}
    salary_value = (salary_info.get("value") or {}) if isinstance(salary_info, dict) else {}
    salary_amount = salary_value.get("value")
    salary_currency = clean_text(salary_info.get("currency", "")) if isinstance(salary_info, dict) else ""
    salary_period = clean_text(salary_value.get("unitText", "")) if isinstance(salary_value, dict) else ""
    if salary_amount is not None:
        amount = _to_number(salary_amount)
        standard["job"]["salary"] = {
            "raw": f"{salary_currency} {salary_amount}".strip(),
            "currency": salary_currency,
            "min": amount,
            "max": amount,
            "period": salary_period,
        }

    standard["source"]["detail_url"] = canonical_url


def _hydrate_from_detail_html(standard: dict, soup: BeautifulSoup, base_url: str | None) -> None:
    header = _extract_main_summary_block(soup)
    sections = _extract_detail_sections(soup)

    if header:
        if not standard["organization"]["name"]:
            standard["organization"]["name"] = header.get("organization", "")
        if not standard["organization"]["logo_url"]:
            standard["organization"]["logo_url"] = _normalize_url(header.get("image", ""), base_url)
        if not standard["location"]["raw"]:
            standard["location"].update(_split_location(header.get("location", "")))
            standard["location"]["raw"] = header.get("location", "")
        if not standard["job"]["salary"]["raw"] and header.get("salary"):
            standard["job"]["salary"] = _build_salary_dict(header["salary"])
        if not standard["dates"]["deadline"]:
            standard["dates"]["deadline"] = header.get("deadline", "")

    standard["sections"].update({
        "overview": header.get("overview", "") if header else "",
        "requirements": sections.get("Requisitos", ""),
        "contract_conditions": sections.get("Condiciones del contrato", ""),
        "how_to_apply": sections.get("Como postular", "") or sections.get("Cómo postular", ""),
        "bases": sections.get("Bases de la convocatoria", ""),
        "position_profile": sections.get("Perfil de puesto", ""),
    })
    standard["raw"]["visible_sections"] = sections

    if not standard["job"]["summary"]:
        standard["job"]["summary"] = header.get("overview", "") if header else ""

    description_parts = [
        standard["job"].get("summary", ""),
        standard["sections"].get("requirements", ""),
        standard["sections"].get("contract_conditions", ""),
        standard["sections"].get("how_to_apply", ""),
    ]
    standard["job"]["description"] = clean_text(" ".join(part for part in description_parts if part))

    _extract_profile_fields(standard, sections)
    standard["attachments"] = _extract_attachments(soup, base_url)
    _fill_application_fields(standard)


def _extract_detail_title(soup: BeautifulSoup, json_ld: dict) -> str:
    if json_ld.get("title"):
        return clean_text(json_ld["title"])
    h1 = soup.select_one("main h1, h1")
    if h1:
        return clean_text(h1.get_text(" ", strip=True))
    meta_title = soup.find("meta", attrs={"name": "title"})
    if meta_title and meta_title.get("content"):
        return clean_text(meta_title["content"])
    return ""


def _extract_main_summary_block(soup: BeautifulSoup) -> dict:
    main = soup.select_one("main")
    if not main:
        return {}

    for card in main.find_all("div", recursive=False):
        h1 = card.select_one("h1")
        if not h1:
            continue

        org_el = card.select_one("h2")
        image_el = card.select_one("img")
        tags = [clean_text(span.get_text(" ", strip=True)) for span in card.select("div.flex.flex-wrap span")]
        meaningful_tags = [tag for tag in tags if tag]

        return {
            "title": clean_text(h1.get_text(" ", strip=True)),
            "organization": clean_text(org_el.get_text(" ", strip=True)) if org_el else "",
            "image": _get_image_src(image_el),
            "location": _find_first_matching_text(meaningful_tags, [r","]),
            "salary": _find_first_matching_text(meaningful_tags, [r"(?:s/?\\.?\\s*/?|pen)\\s*[0-9]"]),
            "deadline": _find_first_matching_text(meaningful_tags, [r"finaliza"]),
            "overview": clean_text(" ".join(meaningful_tags)),
        }

    return {}


def _extract_detail_sections(soup: BeautifulSoup) -> dict[str, str]:
    sections: dict[str, str] = {}
    main = soup.select_one("main")
    if not main:
        return sections

    for card in main.find_all("div", recursive=False):
        heading = card.select_one("h3")
        if not heading:
            continue

        title = clean_text(heading.get_text(" ", strip=True))
        if not title:
            continue

        text = clean_text(card.get_text(" ", strip=True))
        if text.startswith(title):
            text = clean_text(text[len(title):])
        sections[title] = text

        if title.lower() == "bases de la convocatoria":
            break

    return sections


def _extract_profile_fields(standard: dict, sections: dict[str, str]) -> None:
    requirements = sections.get("Requisitos", "")
    contract = sections.get("Condiciones del contrato", "")
    how_to_apply = sections.get("Como postular", "") or sections.get("Cómo postular", "")
    # print('requirements:', requirements)
    standard["profile"]["academic_requirements"] = _extract_labeled_chunk(
        requirements,
        ["Formación Académica", "Requisito mínimo"],
    )
    # Fallback: cuando el bloque usa "Requisitos:" como encabezado genérico,
    # extraer el texto antes de la primera oración de experiencia.
    if not standard["profile"]["academic_requirements"] and requirements:
        standard["profile"]["academic_requirements"] = _extract_pre_experience_text(requirements)
    if not standard["profile"]["target_audience"]:
        standard["profile"]["target_audience"] = standard["profile"]["academic_requirements"]

    standard["profile"]["experience"] = _extract_sentences_with_keywords(requirements, ["Experiencia"])
    standard["profile"]["courses"] = _extract_sentences_with_keywords(
        requirements,
        ["Cursos y/o programas de especialización", "Capacitación"],
    )
    standard["profile"]["knowledge"] = _extract_sentences_with_keywords(requirements, ["Conocimiento"])

    vacancies_text = _extract_labeled_chunk(requirements, ["Número de vacantes", "Nro de vacantes"])
    if vacancies_text:
        standard["job"]["vacancies"] = _extract_first_int(vacancies_text)

    remuneration_text = _extract_labeled_chunk(contract, ["Remuneración"])
    if remuneration_text and not standard["job"]["salary"]["raw"]:
        standard["job"]["salary"] = _build_salary_dict(remuneration_text)

    application_window = _extract_labeled_chunk(how_to_apply, ["Plazo para postular"])
    if application_window:
        standard["dates"]["application_window"] = application_window

    instructions = _extract_labeled_chunk(how_to_apply, ["¿Cómo postular?", "Como postular", "Cómo postular"])
    if instructions:
        standard["application"]["instructions"] = instructions


def _fill_application_fields(standard: dict) -> None:
    instructions = standard["application"].get("instructions", "")
    attachments = standard.get("attachments", [])

    if instructions:
        match = re.search(r"Horario de\s+([^.]*)", instructions, flags=re.IGNORECASE)
        if match:
            standard["application"]["schedule"] = clean_text(match.group(1))

    bases_urls = [attachment["url"] for attachment in attachments if attachment.get("type") == "bases"]
    profile_urls = [attachment["url"] for attachment in attachments if attachment.get("type") == "position_profile"]
    annex_urls = [attachment["url"] for attachment in attachments if attachment.get("type") == "annex"]

    standard["application"]["documents"] = attachments
    standard["application"]["bases_url"] = bases_urls[0] if bases_urls else ""
    standard["application"]["position_profile_url"] = profile_urls[0] if profile_urls else ""
    standard["application"]["annex_urls"] = annex_urls


def _extract_attachments(soup: BeautifulSoup, base_url: str | None) -> list[dict]:
    attachments = []
    seen = set()
    for anchor in soup.select("main a[href]"):
        href = _normalize_url(anchor.get("href", ""), base_url)
        text = clean_text(anchor.get_text(" ", strip=True))
        if not href or href in seen:
            continue
        lower_text = text.lower()
        if any(keyword in lower_text for keyword in ["base", "cronograma", "anexo", "postular", "convocatoria"]):
            attachments.append({
                "label": text,
                "url": href,
                "type": _classify_attachment(text),
            })
            seen.add(href)
    return attachments


def _enrich_listing_item_from_detail(
    item: dict,
    base_url: str | None,
    detail_fetcher: Callable[[str], str | None],
) -> dict:
    detail_url = item.get("url", "")
    if not detail_url:
        return item

    try:
        detail_html = detail_fetcher(detail_url)
    except Exception as error:
        logger.warning(f"No se pudo enriquecer desde detalle '{detail_url}': {error}")
        return item

    if not detail_html:
        return item

    detail_item = _parse_detail_html(detail_html, base_url=detail_url)
    if not detail_item:
        return item

    merged = _merge_extracted_items(item, detail_item)
    merged["id"] = item.get("id", "")
    merged["standardized"]["source"]["page_type"] = "listing+detail"
    return merged


def _parse_detail_html(html: str, base_url: str | None = None) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    json_ld = _extract_job_posting_json_ld(soup)
    canonical_url = _get_canonical_url(soup, base_url)
    return _parse_detail_page(soup, json_ld, base_url, canonical_url)


def _merge_extracted_items(listing_item: dict, detail_item: dict) -> dict:
    merged_standard = _merge_values(
        listing_item.get("standardized", {}),
        detail_item.get("standardized", {}),
    )
    merged_item = _finalize_item(merged_standard)

    # Conserva la URL detalle descubierta desde el listado si la del detalle no existe.
    if not merged_item.get("url") and listing_item.get("url"):
        merged_item["url"] = listing_item["url"]

    return merged_item


def _merge_values(base_value, override_value):
    if isinstance(base_value, dict) and isinstance(override_value, dict):
        merged = {}
        keys = set(base_value) | set(override_value)
        for key in keys:
            merged[key] = _merge_values(base_value.get(key), override_value.get(key))
        return merged

    if isinstance(base_value, list) and isinstance(override_value, list):
        return override_value if override_value else base_value

    if _has_meaningful_value(override_value):
        return override_value
    return base_value


def _has_meaningful_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, set, tuple)):
        return bool(value)
    return True


def _extract_apply_url(soup: BeautifulSoup, base_url: str | None) -> str:
    for anchor in soup.select("main a[href]"):
        text = clean_text(anchor.get_text(" ", strip=True)).lower()
        if any(keyword in text for keyword in ["postular", "aplicar", "bases", "convocatoria completa"]):
            return _normalize_url(anchor.get("href", ""), base_url)
    return ""


def _extract_job_posting_json_ld(soup: BeautifulSoup) -> dict:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidate = _find_job_posting_node(data)
        if candidate:
            return candidate
    return {}


def _find_job_posting_node(data) -> dict:
    if isinstance(data, dict):
        if str(data.get("@type", "")).lower() == "jobposting":
            return data
        for value in data.values():
            candidate = _find_job_posting_node(value)
            if candidate:
                return candidate

    if isinstance(data, list):
        for item in data:
            candidate = _find_job_posting_node(item)
            if candidate:
                return candidate

    return {}


def _find_best_detail_link(el: Tag) -> Tag | None:
    for anchor in el.select("a[href]"):
        href = anchor.get("href", "")
        if re.search(r"proceso|convocatoria|empleo|trabajo", href, flags=re.IGNORECASE):
            return anchor
    return el.select_one("h1 a[href], h2 a[href], h3 a[href], a[href]")


def _extract_labeled_text(el: Tag, label: str) -> str:
    matches = []
    for node in el.find_all(["a", "p", "div", "span"]):
        text = clean_text(node.get_text(" ", strip=True))
        if label.lower() not in text.lower():
            continue
        parts = re.split(rf"{re.escape(label)}\s*:\s*", text, flags=re.IGNORECASE)
        if len(parts) > 1:
            extracted = clean_text(parts[-1])
            if extracted:
                matches.append(extracted)

    if not matches:
        return ""

    # Prefiere la coincidencia más específica para evitar arrastrar texto del card completo.
    return min(matches, key=len)


def _extract_location_from_listing(el: Tag) -> str:
    for span in el.select("span"):
        text = clean_text(span.get_text(" ", strip=True))
        if text and "," in text and len(text) < 80:
            return text
    return ""


def _extract_salary_from_listing(el: Tag) -> str:
    for span in el.select("span"):
        text = clean_text(span.get_text(" ", strip=True))
        if re.search(r"(?:s/?\.?\s*/?|pen)\s*[0-9]", text, flags=re.IGNORECASE):
            return text
    return ""


def _extract_deadline_from_listing(el: Tag) -> str:
    for span in el.select("span"):
        text = clean_text(span.get_text(" ", strip=True))
        if "finaliza" in text.lower():
            return text
    return ""


def _classify_attachment(label: str) -> str:
    normalized = clean_text(label).lower()
    if "perfil" in normalized and "puesto" in normalized:
        return "position_profile"
    if "anexo" in normalized:
        return "annex"
    if "base" in normalized or "cronograma" in normalized or "convocatoria" in normalized:
        return "bases"
    return "other"


def _build_salary_dict(raw_salary: str) -> dict:
    normalized = raw_salary.replace(",", "")
    numbers = re.findall(r"\d+(?:[.]\d+)?", normalized)
    amount = _to_number(numbers[0]) if numbers else None
    currency = "PEN" if re.search(r"(?:s/?\.?\s*/?|soles|pen)", raw_salary, flags=re.IGNORECASE) else ""
    return {
        "raw": clean_text(raw_salary),
        "currency": currency,
        "min": amount,
        "max": amount,
        "period": "MONTH" if amount is not None else "",
    }


def _split_location(raw_location: str) -> dict:
    parts = [clean_text(part) for part in raw_location.split(",") if clean_text(part)] if raw_location else []
    district = parts[0] if parts else ""
    region = parts[-1] if len(parts) > 1 else (parts[0] if parts else "")
    city = parts[0] if parts else ""
    return {
        "district": district,
        "city": city,
        "region": region,
        "country": "Perú" if raw_location else "",
    }


def _get_canonical_url(soup: BeautifulSoup, base_url: str | None) -> str:
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        return _normalize_url(canonical["href"], base_url)

    og_url = soup.find("meta", attrs={"property": "og:url"})
    if og_url and og_url.get("content"):
        return _normalize_url(og_url["content"], base_url)

    return base_url or ""


def _extract_site_name(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "og:site_name"})
    if meta and meta.get("content"):
        return clean_text(meta["content"])
    return ""


def _get_image_src(image_el: Tag | None) -> str:
    if not image_el:
        return ""
    return image_el.get("src") or image_el.get("data-src") or image_el.get("data-lazy") or ""


def _normalize_url(url: str, base_url: str | None) -> str:
    if not url:
        return ""
    if base_url:
        return urljoin(base_url, url)
    return url


def _extract_labeled_chunk(text: str, labels: list[str]) -> str:
    for label in labels:
        pattern = rf"{re.escape(label)}\s*:\s*(.*?)(?=(?:[A-ZÁÉÍÓÚÑ¿][^:]{1,40}:)|$)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    return ""


def _extract_pre_experience_text(text: str) -> str:
    """
    Extrae el requisito académico cuando no hay etiqueta explícita
    ("Formación Académica:", "Requisito mínimo:").

    Estrategia: elimina el prefijo del bloque ("Requisitos:", "Perfil del
    puesto:") y toma el texto hasta la primera oración de experiencia.
    Cubre el patrón habitual de las convocatorias peruanas donde el primer
    renglón tras "Requisitos:" es el título académico requerido.
    """
    prefix = re.compile(r"(?i)^(requisitos?|perfil\s+del\s+puesto)\s*:\s*")
    cleaned = prefix.sub("", text).strip()
    if not cleaned:
        return ""
    # Detener antes del primer bloque de experiencia
    exp_stop = re.search(
        r"\bExperiencia\s+(?:general|espec[ií]fica|laboral|en\s+el|m[ií]nima)\b",
        cleaned,
        re.IGNORECASE,
    )
    if exp_stop:
        candidate = cleaned[:exp_stop.start()].strip(" .;:")
    else:
        # No hay sección de experiencia: tomar hasta el primer separador fuerte
        period = re.search(r"\.\s+[A-ZÁÉÍÓÚÑ]", cleaned)
        candidate = cleaned[:period.start() + 1] if period else cleaned
    return clean_text(candidate)


def _extract_sentences_with_keywords(text: str, keywords: list[str]) -> list[str]:
    results = []
    for sentence in re.split(r"(?<=[.;])\s+", text):
        cleaned = clean_text(sentence)
        if cleaned and any(keyword.lower() in cleaned.lower() for keyword in keywords):
            results.append(cleaned)
    return results


def _extract_first_int(text: str) -> int | None:
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def _find_first_matching_text(values: list[str], patterns: list[str]) -> str:
    for value in values:
        for pattern in patterns:
            if re.search(pattern, value, flags=re.IGNORECASE):
                return clean_text(value)
    return ""


def _to_number(value) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def clean_text(text: str) -> str:
    """Limpia texto, espacios y entidades residuales frecuentes."""
    if not text:
        return ""
    text = text.replace("\xad", "")
    text = text.replace("&shy;", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_slug_from_url(url: str) -> str:
    """
    Extrae el slug de una URL.
    Ejemplo: "https://convocatorias.pe/proceso-seleccion-xxx.html" → "proceso-seleccion-xxx"
    """
    if not url:
        return ""
    # Obtener el path de la URL
    path = urlparse(url).path
    # Obtener el nombre sin extensión
    slug = Path(path).stem
    return slug if slug else ""


def slugify(text: str) -> str:
    """
    Convierte un título en un slug URL-friendly.
    Ejemplo: "Hola Mundo! 123" → "hola-mundo-123"
    """
    # Convierte a minúsculas
    text = text.lower().strip()
    # Reemplaza caracteres especiales del español
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u", "à": "a", "è": "e", "ì": "i",
        "ò": "o", "ù": "u",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Reemplaza todo lo que no sea letra, número o guion
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    # Reemplaza espacios por guiones
    text = re.sub(r"[\s_-]+", "-", text)
    # Elimina guiones al inicio y al final
    text = text.strip("-")
    # Limita a 80 caracteres
    return text[:80]

