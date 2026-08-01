

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

# from src.data.careers import extract_careers_from_education
from src.utils.careers_utils import extract_careers_from_education
from src.utils.data_utils import _extract_codigo_from_title, _parse_datetime, _safe_int, _format_spanish_date, tiene_colegiatura, obtener_sueldo
from src.utils.requirements_parser import get_requirements_blob, parse_education, parse_experience, parse_courses, parse_knowledge
from src.utils.nivel_academico_utils import extract_academic_level_from_education




@dataclass
class Organization:
    name: str
    logo_url: Optional[str] = None
    sector: Optional[str] = None


@dataclass
class Location:
    country: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    raw: Optional[str] = None


@dataclass
class Salary:
    currency: Optional[str] = None
    amount: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    period: Optional[str] = None
    raw: Optional[str] = None


@dataclass
class Experience:
    general_years: int = 0
    specific_years: int = 0
    details: List[str] = field(default_factory=list)


@dataclass
class Requirements:
    education: List[str] = field(default_factory=list)
    academic_level: List[str] = field(default_factory=list)
    colegiatura: str = ""
    careers: List[str] = field(default_factory=list)  # Carreras asociadas a la educación requerida
    experience: Experience = field(default_factory=Experience)
    courses: List[str] = field(default_factory=list)
    knowledge: List[str] = field(default_factory=list)
    other: List[str] = field(default_factory=list)


@dataclass
class Document:
    label: str
    url: str
    type: Optional[str] = None


@dataclass
class Application:
    instructions: Optional[str] = None
    apply_url: Optional[str] = None
    bases_url: Optional[str] = None
    documents: List[Document] = field(default_factory=list)


@dataclass
class Employment:
    type: Optional[str] = None
    contract_mode: Optional[str] = None


@dataclass
class Dates:
    date_posted: Optional[str] = None  # ISO string
    deadline: Optional[str] = None     # ISO string
    deadline_text: Optional[str] = None
    application_window_text: Optional[str] = None


@dataclass
class Source:
    site: Optional[str] = None
    canonical_url: Optional[str] = None
    detail_url: Optional[str] = None


@dataclass
class ConvocatoriaV2:
    schema_version: str = "2.0"

    id: str = ""
    title: str = ""
    codigo: str = ""
    slug: str = ""
    summary: str = ""

    organization: Organization = field(default_factory=lambda: Organization(name=""))
    employment: Employment = field(default_factory=Employment)
    vacancies: int = 0

    location: Location = field(default_factory=Location)
    salary: Salary = field(default_factory=Salary)
    dates: Dates = field(default_factory=Dates)

    requirements: Requirements = field(default_factory=Requirements)
    application: Application = field(default_factory=Application)
    source: Source = field(default_factory=Source)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_source(item: Dict[str, Any]) -> "ConvocatoriaV2":
        """
        Construye ConvocatoriaV2 a partir del JSON grande (como el que compartiste).
        Priorización (canónica):
          - title/slug/url/date: raíz
          - standardized.job.salary/vacancies/summary/employment_type
          - standardized.organization/location/dates/application/attachments
          - raw.json_ld como respaldo (solo si falta algo)
        """
        std = (item.get("standardized") or {})
        job = (std.get("job") or {})
        org = (std.get("organization") or {})
        loc = (std.get("location") or {})
        dates = (std.get("dates") or {})
        app = (std.get("application") or {})
        src = (std.get("source") or {})
        profile = (std.get("profile") or {})
        raw = (std.get("raw") or {})
        json_ld = (raw.get("json_ld") or {})

        

        # Identidad
        slug = item.get("slug") or job.get("slug") or ""
        canonical_url = src.get("canonical_url") or item.get("url") or src.get("url") or ""
        _id = slug or canonical_url

        # Organización
        organization = Organization(
            name=org.get("name") or (json_ld.get("hiringOrganization") or {}).get("name") or "",
            logo_url=org.get("logo_url") or (json_ld.get("hiringOrganization") or {}).get("logo"),
            sector=org.get("sector")
        )

        # Ubicación
        location = Location(
            raw=loc.get("raw"),
            city=loc.get("city") or (json_ld.get("jobLocation") or {}).get("address", {}).get("addressLocality"),
            region=loc.get("region") or (json_ld.get("jobLocation") or {}).get("address", {}).get("addressRegion"),
            country=loc.get("country") or (json_ld.get("jobLocation") or {}).get("address", {}).get("addressCountry"),
            district=loc.get("district"),
            province=None
        )

        # Empleo
        employment = Employment(
            type=job.get("employment_type") or json_ld.get("employmentType"),
            contract_mode=job.get("employment_type") or json_ld.get("employmentType")
        )

        # Vacantes — mínimo 1 cuando el dato no está disponible
        vacancies = _safe_int(job.get("vacancies") or item.get("vacancies") or 1, default=1)

        # Sueldo
        sections = (std.get("sections") or {})
        contract_conditions = (sections.get("contract_conditions") or {})
        sueldo_conditions_raw = obtener_sueldo(contract_conditions)
        
        sal = job.get("salary") or {}
        salary = Salary(
            currency=sal.get("currency") or (json_ld.get("baseSalary") or {}).get("currency") or "PEN",
            amount=sal.get("amount") or sueldo_conditions_raw or sal.get("min") or sal.get("max"),
            min=sal.get("min"),
            max=sal.get("max"),
            period=sal.get("period") or "MONTH",
            raw=sal.get("raw")
        )

        # Fechas
        deadline_iso = _parse_datetime(dates.get("deadline") or json_ld.get("validThrough") or item.get("date"))
        dates_obj = Dates(
            date_posted=_parse_datetime(dates.get("published_at") or json_ld.get("datePosted")),
            deadline=deadline_iso,
            deadline_text=_format_spanish_date(deadline_iso),
            application_window_text=dates.get("application_window")
        )

        # Requirements: segmentación robusta desde el blob de requisitos
        requirements_blob   = get_requirements_blob(std)
        education           = parse_education(requirements_blob, profile)
        academic_level      = extract_academic_level_from_education(education)
        colegiatura         = tiene_colegiatura(education)
        careers             = extract_careers_from_education(education)
        exp_details         = parse_experience(requirements_blob, profile)
        courses             = parse_courses(requirements_blob, profile)
        knowledge           = parse_knowledge(requirements_blob, profile)

        requirements = Requirements(
            education           = education,
            academic_level      = academic_level,
            colegiatura         = colegiatura,
            careers             = careers,
            experience          = Experience(
                                    general_years   = 0,   # si luego parseas "03 años", lo llenas aquí
                                    specific_years  = 0,  # idem
                                    details         = exp_details
                                ),
            courses             = courses,
            knowledge           = knowledge,
            other               = []
        )

        # Application + documents (unificamos attachments + application.documents sin duplicar por URL)
        documents: List[Document] = []
        seen_urls = set()

        # Preferimos application.documents si existe
        for d in (app.get("documents") or []):
            if not isinstance(d, dict):
                continue
            url = d.get("url")
            if not url or url in seen_urls:
                continue
            # Si la URL empieza con 'https://www.convocatorias.pe', usar '#'
            doc_url = '#' if url.startswith('https://www.convocatorias.pe') else url
            documents.append(Document(label=d.get("label") or "Documento", url=doc_url, type=d.get("type")))
            seen_urls.add(url)

        # Luego attachments como fallback
        for a in (std.get("attachments") or []):
            if not isinstance(a, dict):
                continue
            url = a.get("url")
            if not url or url in seen_urls:
                continue
            doc_url = '#' if url.startswith('https://www.convocatorias.pe') else url
            documents.append(Document(label=a.get("label") or "Documento", url=doc_url, type=a.get("type")))
            seen_urls.add(url)

        application = Application(
            instructions=app.get("instructions"),
            apply_url=src.get("apply_url") or app.get("apply_url"),
            bases_url=app.get("bases_url"),
            documents=documents
        )

        source_obj = Source(
            site=src.get("site"),
            canonical_url=canonical_url,
            detail_url=src.get("detail_url") or canonical_url
        )

        # Summary canónico
        summary = job.get("summary") or item.get("content") or ""
        summary = summary.strip()

        # Titulo
        raw_title = job.get("title") or json_ld.get("title") or item.get("title") or ""
        raw_title = raw_title.strip()
        
        # Código
        codigo = _extract_codigo_from_title(raw_title)

        # Title v1
        title_after_colon = raw_title.split(":", 1)[-1].strip() if ":" in raw_title else raw_title
        emp_type = employment.type or ""
        
        title_v1 = f"{codigo} - {title_after_colon} ({emp_type}) [{organization.name}]".strip()
        # title_v2 = f"{title_after_colon} ({emp_type} - {codigo}) [{organization.name}]".strip()
        
        meta = " - ".join(p for p in [emp_type, codigo] if p)
        title_v2 = " ".join(filter(None, [
            title_after_colon,
            f"({meta})" if meta else None,
            f"[{organization.name}]" if organization and organization.name else None,
        ])).strip()

        return ConvocatoriaV2(
            id=item.get("id"),
            title=title_v2,
            codigo=codigo,
            slug=slug,
            summary=summary,
            organization=organization,
            employment=employment,
            vacancies=vacancies,
            location=location,
            salary=salary,
            dates=dates_obj,
            requirements=requirements,
            application=application,
            source=source_obj
        )