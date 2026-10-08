"""Retrieve journal metadata with explicit dates and incomplete coverage reporting.

Standard library only. Run with -h for arguments. No topic or article type filter
is applied. Publisher verification and clinical appraisal are separate steps.
"""

import argparse
import calendar
import copy
import csv
import datetime as dt
import html
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


BEIJING = dt.timezone(dt.timedelta(hours=8))
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CROSSREF = "https://api.crossref.org/journals/"
BUCKETS = ("articles", "late_indexed", "date_uncertain", "outside_window")


def now_iso():
    return dt.datetime.now(BEIJING).isoformat(timespec="seconds")


def clean_text(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value or "")).split())


def xml_text(node):
    return "" if node is None else " ".join("".join(node.itertext()).split())


def normalized_doi(value):
    value = (value or "").strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.lower()


def date_value(parts):
    """Preserve missing date components instead of inventing a publication day."""
    try:
        numbers = [int(x) for x in parts]
        if not numbers or len(numbers) > 3:
            return None, "unknown"
        dt.date(numbers[0], numbers[1] if len(numbers) > 1 else 1,
                numbers[2] if len(numbers) > 2 else 1)
        value = str(numbers[0]).zfill(4)
        value += "".join("-" + str(x).zfill(2) for x in numbers[1:])
        return value, ("year", "month", "day")[len(numbers) - 1]
    except (ValueError, TypeError, OverflowError):
        return None, "unknown"


def evidence(source, kind, field, parts=None, raw=None):
    value, precision = date_value(parts or [])
    return {"source": source, "kind": kind, "field": field,
            "value": value, "precision": precision, "raw": raw}


def xml_date(node, kind, field):
    raw = {child.tag: xml_text(child) for child in node}
    year, month, day = (raw.get(key) for key in ("Year", "Month", "Day"))
    if month and not month.isdigit():
        months = {name.lower(): i for names in (calendar.month_abbr, calendar.month_name)
                  for i, name in enumerate(names) if i}
        month = months.get(month.lower())
    parts = [year]
    if month is not None:
        parts.append(month)
        if day is not None:
            parts.append(day)
    result = evidence("pubmed", kind, field, parts, raw)
    if not year or (raw.get("Month") and month is None):
        result.update(value=None, precision="unknown")
    return result


def empty_record(journal, source, record_id, url, query):
    return {"journal_ids": [journal["id"]], "journal_names": [journal["name"]],
            "doi": "", "pmids": [], "title": "", "authors": [],
            "abstract": "", "abstracts": [], "publication_types": [],
            "date_evidence": [], "metadata_warnings": [],
            "retrieval_sources": [{"source": source, "record_id": record_id,
                                   "journal_id": journal["id"], "url": url,
                                   "query": query, "retrieved_at": now_iso()}]}


def parse_pubmed(data, journal, query):
    root = ET.fromstring(data)
    error = root.find(".//ERROR")
    if error is not None:
        raise ValueError("PubMed EFetch returned an error")
    records = []
    for item in root.findall("PubmedArticle"):
        citation = item.find("MedlineCitation")
        article = citation.find("Article") if citation is not None else None
        if article is None:
            continue
        pmid = xml_text(citation.find("PMID"))
        url = "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/"
        record = empty_record(journal, "pubmed", pmid, url, query)
        record["pmids"] = [pmid] if pmid else []
        record["title"] = xml_text(article.find("ArticleTitle"))
        for author in article.findall("AuthorList/Author"):
            name = xml_text(author.find("CollectiveName"))
            if not name:
                name = " ".join(filter(None, [xml_text(author.find("ForeName")),
                                              xml_text(author.find("LastName"))]))
            if name:
                record["authors"].append(name)
        abstract = []
        for section in article.findall("Abstract/AbstractText"):
            label = section.get("Label", "")
            abstract.append((label + ": " if label else "") + xml_text(section))
        record["abstract"] = "\n".join(abstract)
        if abstract:
            record["abstracts"].append({"source": "pubmed", "text": record["abstract"]})
        record["publication_types"] = [xml_text(x) for x in article.findall(
            "PublicationTypeList/PublicationType")]
        doi_nodes = item.findall("PubmedData/ArticleIdList/ArticleId")
        doi_nodes += article.findall("ELocationID")
        dois = sorted({normalized_doi(xml_text(x)) for x in doi_nodes
                       if (x.get("IdType") or x.get("EIdType")) == "doi" and xml_text(x)})
        if dois:
            record["doi"] = dois[0]
            if len(dois) > 1:
                record["metadata_warnings"].append("Multiple DOIs in PubMed record: " + ", ".join(dois))
        for node in article.findall("ArticleDate"):
            kind = "online" if node.get("DateType") == "Electronic" else "print"
            record["date_evidence"].append(xml_date(node, kind, "ArticleDate/" + node.get("DateType", "unknown")))
        node = article.find("Journal/JournalIssue/PubDate")
        if node is not None:
            model = article.get("PubModel", "")
            kind = "print" if "Print" in model else "issue"
            record["date_evidence"].append(xml_date(node, kind, "JournalIssue/PubDate"))
        status_kinds = {"epublish": "online", "aheadofprint": "online", "ppublish": "print",
                        "entrez": "created", "pubmed": "entry", "medline": "indexing"}
        for node in item.findall("PubmedData/History/PubMedPubDate"):
            status = node.get("PubStatus", "")
            if status in status_kinds:
                record["date_evidence"].append(xml_date(node, status_kinds[status], "History/" + status))
        records.append(record)
    return records


def parse_crossref(item, journal, query):
    doi = normalized_doi(item.get("DOI"))
    url = "https://doi.org/" + doi if doi else item.get("URL", "")
    record = empty_record(journal, "crossref", doi, url, query)
    record["doi"] = doi
    record["title"] = clean_text(" ".join(item.get("title") or []))
    record["authors"] = [" ".join(filter(None, [a.get("given"), a.get("family")])) or a.get("name", "")
                         for a in item.get("author", [])]
    record["abstract"] = clean_text(item.get("abstract"))
    if record["abstract"]:
        record["abstracts"] = [{"source": "crossref", "text": record["abstract"]}]
    record["publication_types"] = [item["type"]] if item.get("type") else []
    fields = {"published-online": "online", "published-print": "print", "published": "publication",
              "issued": "issue", "created": "created", "indexed": "indexing", "deposited": "deposited"}
    for field, kind in fields.items():
        raw = item.get(field)
        if not isinstance(raw, dict):
            continue
        parts_list = raw.get("date-parts") or []
        if not parts_list and raw.get("date-time"):
            parts_list = [raw["date-time"][:10].split("-")]
        for parts in parts_list or [[]]:
            record["date_evidence"].append(evidence("crossref", kind, field, parts, raw))
    return record


class Client:
    def __init__(self, interval):
        self.interval = interval
        self.last_request = 0.0
        self.requests = 0

    def request(self, url, params, post=False):
        payload = urllib.parse.urlencode(params).encode("utf-8")
        address = url if post else url + "?" + payload.decode("ascii")
        request = urllib.request.Request(address, data=payload if post else None,
                                         headers={"User-Agent": "comment-letter-scout/1.0",
                                                  "Accept": "application/json, application/xml, text/xml"})
        for attempt in range(3):
            time.sleep(max(0.0, self.interval - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            self.requests += 1
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                message = "HTTP " + str(exc.code)
                retryable = exc.code in (408, 429) or exc.code >= 500
                delay = exc.headers.get("Retry-After", "") if exc.headers else ""
                delay = min(30.0, float(delay)) if delay.isdigit() else 2 ** (attempt + 1)
                if not retryable or attempt == 2:
                    raise RuntimeError(message) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                message, delay = "Network request failed or timed out", 2 ** (attempt + 1)
                if attempt == 2:
                    raise RuntimeError(message) from None
            time.sleep(delay)


def source_coverage():
    return {"status": "ok", "retrieved_count": 0, "expected_count": None,
            "request_count": 0, "queries": [], "errors": [], "warnings": []}


def finish_coverage(coverage, count, completed, requests):
    coverage["retrieved_count"] = count
    coverage["request_count"] = requests
    if coverage["errors"]:
        coverage["status"] = "partial" if completed or count else "error"
    return coverage


def pubmed_query(journal, start, end):
    date_range = start.strftime("%Y/%m/%d") + ":" + end.strftime("%Y/%m/%d")
    dates = " OR ".join(date_range + "[" + field + "]" for field in ("dp", "epdat", "crdt"))
    return "(" + journal["pubmed_query"] + ") AND (" + dates + ")"


def fetch_pubmed(journal, start, end, client):
    coverage, records, ids = source_coverage(), [], []
    before, completed = client.requests, 0
    query = pubmed_query(journal, start, end)
    coverage["queries"].append(query)
    try:
        offset = 0
        while True:
            params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": min(1000, 9999 - offset),
                      "retstart": offset, "tool": "comment-letter-scout"}
            response = json.loads(client.request(EUTILS + "esearch.fcgi", params))
            result = response.get("esearchresult", {})
            if "count" not in result or result.get("errorlist") or response.get("error"):
                raise ValueError("PubMed ESearch returned an error or invalid result")
            count = int(result["count"])
            coverage["expected_count"] = count
            if result.get("warninglist"):
                coverage["warnings"].append(result["warninglist"])
            page = result.get("idlist", [])
            if not page and offset < min(count, 9999):
                raise ValueError("PubMed ESearch stopped before the expected count")
            ids.extend(page)
            offset += len(page)
            if offset >= min(count, 9999):
                if count > 9999:
                    coverage["errors"].append("PubMed 9999-record retrieval limit reached; rerun a narrower window")
                break
        completed += 1
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        coverage["errors"].append("PubMed ESearch failed: " + str(exc))
    ids = list(dict.fromkeys(ids))
    for offset in range(0, len(ids), 100):
        batch = ids[offset:offset + 100]
        try:
            data = client.request(EUTILS + "efetch.fcgi", {"db": "pubmed", "id": ",".join(batch),
                                  "retmode": "xml", "tool": "comment-letter-scout"}, post=True)
            parsed = parse_pubmed(data, journal, query)
            records.extend(parsed)
            found = {pmid for record in parsed for pmid in record["pmids"]}
            if found != set(batch):
                coverage["errors"].append("EFetch omitted or added records in batch at offset " + str(offset))
            completed += 1
        except (RuntimeError, ValueError, ET.ParseError, KeyError, TypeError) as exc:
            coverage["errors"].append("PubMed EFetch batch " + str(offset) + " failed: " + str(exc))
    return records, finish_coverage(coverage, len(records), completed, client.requests - before)


def fetch_crossref(journal, start, end, client, rows=1000):
    coverage, records = source_coverage(), []
    before, completed, total = client.requests, 0, 0
    issns = list(dict.fromkeys(journal.get("issns", [])))
    if not issns:
        coverage["errors"].append("No ISSN configured")
    for issn in issns:
        cursor, seen, received = "*", set(), 0
        filters = "from-online-pub-date:" + start.isoformat() + ",until-online-pub-date:" + end.isoformat()
        query = {"issn": issn, "filter": filters}
        coverage["queries"].append(query)
        try:
            while True:
                data = json.loads(client.request(CROSSREF + urllib.parse.quote(issn, safe="") + "/works",
                                  {"filter": filters, "rows": rows, "cursor": cursor}))
                message = data.get("message", {})
                if data.get("status") != "ok" or not isinstance(message.get("items"), list):
                    raise ValueError("Crossref returned an invalid result")
                items = message["items"]
                expected = int(message.get("total-results", 0))
                if cursor == "*":
                    total += expected
                fresh = 0
                for item in items:
                    identity = item.get("DOI") or json.dumps(item, sort_keys=True)
                    if identity not in seen:
                        seen.add(identity)
                        records.append(parse_crossref(item, journal, query))
                        fresh += 1
                received += len(items)
                if items and not fresh:
                    raise ValueError("Crossref pagination repeated records without progress")
                if len(items) < rows:
                    if received < expected:
                        coverage["errors"].append("Crossref ended below reported total for ISSN " + issn)
                    completed += 1
                    break
                cursor = message.get("next-cursor")
                if not cursor:
                    if received < expected:
                        raise ValueError("Crossref pagination ended without a cursor")
                    completed += 1
                    break
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            coverage["errors"].append("Crossref ISSN " + issn + " failed: " + str(exc))
    coverage["expected_count"] = total if completed or records else None
    coverage["count_note"] = "Counts sum ISSN queries and can include duplicate DOIs across ISSNs."
    return records, finish_coverage(coverage, len(records), completed, client.requests - before)


def merge_record(target, source):
    target["doi"] = target["doi"] or source["doi"]
    for field in ("journal_ids", "journal_names", "pmids", "publication_types", "date_evidence",
                  "retrieval_sources", "abstracts", "metadata_warnings"):
        for value in source[field]:
            if value not in target[field]:
                target[field].append(copy.deepcopy(value))
    for field in ("title", "authors"):
        if not target[field]:
            target[field] = copy.deepcopy(source[field])
    if len(source["abstract"]) > len(target["abstract"]):
        target["abstract"] = source["abstract"]


def deduplicate(records):
    """Merge by DOI, then compatible PMID; a shared title never establishes identity."""
    groups = []
    for original in sorted(records, key=lambda r: not bool(r["doi"])):
        record = copy.deepcopy(original)
        exact = [g for g in groups if record["doi"] and g["doi"] == record["doi"]]
        by_pmid = [g for g in groups if set(record["pmids"]) & set(g["pmids"])]
        compatible = [g for g in by_pmid if not record["doi"] or not g["doi"] or g["doi"] == record["doi"]]
        if len({g["doi"] for g in compatible if g["doi"]}) > 1:
            compatible = []
            record["metadata_warnings"].append("PMID matches multiple different DOIs; identity not merged")
        for group in by_pmid:
            if record["doi"] and group["doi"] and group["doi"] != record["doi"]:
                warning = "Shared PMID has conflicting DOIs; identity not merged"
                if warning not in group["metadata_warnings"]:
                    group["metadata_warnings"].append(warning)
                record["metadata_warnings"].append(warning)
        matches = exact + [g for g in compatible if g not in exact]
        if not matches:
            groups.append(record)
            continue
        target = matches[0]
        merge_record(target, record)
        for other in matches[1:]:
            merge_record(target, other)
            groups.remove(other)
    for index, record in enumerate(groups, 1):
        record["id"] = ("doi:" + record["doi"] if record["doi"] else
                        "pmid:" + record["pmids"][0] if record["pmids"] else "unidentified:" + str(index))
    return groups


def classify(record, start, end):
    record["selected_publication_date"] = None
    record["publication_date_basis"] = None
    date_rows = record["date_evidence"]
    preferred = []
    for kind in ("online", "print", "publication", "issue"):
        preferred = [row for row in date_rows if row["kind"] == kind]
        if preferred:
            record["publication_date_basis"] = kind
            break
    exact = {row["value"] for row in preferred if row["precision"] == "day"}
    if not preferred:
        reason = "No publication date available"
    elif len(exact) > 1:
        reason = "Conflicting dates for the preferred publication date type"
    elif not exact:
        reason = "Publication date lacks a verified day"
    else:
        value = next(iter(exact))
        incompatible = [row for row in preferred if not row["value"] or not value.startswith(row["value"])]
        if incompatible:
            reason = "Unknown or inconsistent preferred publication date evidence"
        else:
            selected = dt.date.fromisoformat(value)
            record["selected_publication_date"] = value
            record["date_reason"] = ("Electronic publication date available" if record["publication_date_basis"] == "online"
                                     else "Non-electronic date fallback; publisher must verify first online publication")
            if start <= selected <= end:
                if record["publication_date_basis"] == "online":
                    return "articles"
                record["date_reason"] = "Only a non-electronic publication date is in the window; first online date needs publisher verification"
                return "date_uncertain"
            newly_added = any(row["kind"] in ("created", "entry") and row["precision"] == "day"
                              and start.isoformat() <= row["value"] <= end.isoformat() for row in date_rows)
            if selected < start and newly_added:
                record["date_reason"] = "Older publication newly created or entered in a metadata source during this window"
                return "late_indexed"
            record["date_reason"] = "Preferred publication date is outside the requested window"
            return "outside_window"
    record["date_reason"] = reason
    return "date_uncertain"


def load_registry(path, selected):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    journals = data.get("journals")
    if not isinstance(journals, list) or not journals:
        raise ValueError("Registry must contain a nonempty journals list")
    seen = set()
    for journal in journals:
        for field in ("id", "name", "pubmed_query"):
            if not isinstance(journal.get(field), str) or not journal[field].strip():
                raise ValueError("Registry journal missing required string: " + field)
        if journal["id"] in seen:
            raise ValueError("Duplicate journal id: " + journal["id"])
        seen.add(journal["id"])
        for field in ("issns", "publisher_latest_urls"):
            if not isinstance(journal.get(field), list) or not all(isinstance(x, str) for x in journal[field]):
                raise ValueError("Registry journal requires a string list: " + field)
    if selected:
        unknown = set(selected) - seen
        if unknown:
            raise ValueError("Unknown journal ids: " + ", ".join(sorted(unknown)))
        journals = [journal for journal in journals if journal["id"] in selected]
    return journals


def save_output(output, destination):
    json_path = destination if destination.suffix.lower() == ".json" else destination / "retrieval.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_path = json_path.with_name(json_path.stem + "_candidates.csv")
    fields = ["category", "journal", "title", "doi", "pmid", "publication_date", "date_basis", "date_reason", "sources", "url"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for category in BUCKETS:
            for record in output[category]:
                writer.writerow({"category": category, "journal": "; ".join(record["journal_names"]),
                                 "title": record["title"], "doi": record["doi"], "pmid": "; ".join(record["pmids"]),
                                 "publication_date": record["selected_publication_date"],
                                 "date_basis": record["publication_date_basis"], "date_reason": record["date_reason"],
                                 "sources": "; ".join(sorted({r["source"] for r in record["retrieval_sources"]})),
                                 "url": "https://doi.org/" + record["doi"] if record["doi"] else record["retrieval_sources"][0]["url"]})
    return json_path, csv_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, add_help=False, allow_abbrev=False)
    parser.add_argument("-h", action="help", help="Show this help")
    parser.add_argument("-registry", type=Path, default=Path(__file__).resolve().parents[1] / "references" / "journals.json")
    parser.add_argument("-out", type=Path, required=True, help="Output directory or JSON file path")
    parser.add_argument("-days", type=int, default=5, help="Inclusive calendar days, default 5")
    parser.add_argument("-end", type=dt.date.fromisoformat, help="YYYY-MM-DD, default today in Beijing")
    parser.add_argument("-journals", help="Comma separated journal ids; default all registry journals")
    parser.add_argument("-sources", default="pubmed,crossref", help="Comma separated sources: pubmed,crossref")
    args = parser.parse_args(argv)
    if args.days < 1:
        parser.error("-days must be positive")
    sources = list(dict.fromkeys(x.strip() for x in args.sources.split(",") if x.strip()))
    if not sources or set(sources) - {"pubmed", "crossref"}:
        parser.error("-sources must contain pubmed and/or crossref")
    end = args.end or dt.datetime.now(BEIJING).date()
    try:
        start = end - dt.timedelta(days=args.days - 1)
        selected = [x.strip() for x in args.journals.split(",") if x.strip()] if args.journals else None
        journals = load_registry(args.registry, selected)
    except (OSError, ValueError, OverflowError) as exc:
        parser.error(str(exc))
    output = {"schema_version": 1, "retrieved_at": now_iso(),
              "window": {"start": start.isoformat(), "end": end.isoformat(), "days": args.days,
                         "timezone": "Asia/Shanghai", "inclusive": True},
              "coverage": [], "limitations": [
                  "Metadata retrieval is not publisher verification or a submission recommendation.",
                  "Crossref is searched by reported online publication date only; missing deposits can be absent.",
                  "PubMed date searches include creation dates to capture delayed indexing.",
                  "All publication types are retained. Non-electronic date fallbacks require publisher verification."]}
    output.update({key: [] for key in BUCKETS})
    clients = {"pubmed": Client(0.4), "crossref": Client(1.0)}
    records = []
    for journal in journals:
        coverage = {"journal_id": journal["id"], "journal_name": journal["name"],
                    "publisher_status": "pending", "publisher_latest_urls": journal["publisher_latest_urls"]}
        for source in ("pubmed", "crossref"):
            if source not in sources:
                coverage[source] = {"status": "not_requested", "retrieved_count": None}
                continue
            print(journal["id"] + ": retrieving " + source, file=sys.stderr, flush=True)
            fetch = fetch_pubmed if source == "pubmed" else fetch_crossref
            fetched, coverage[source] = fetch(journal, start, end, clients[source])
            records.extend(fetched)
        output["coverage"].append(coverage)
    for record in deduplicate(records):
        category = classify(record, start, end)
        record["category"] = category
        output[category].append(record)
    for category in BUCKETS:
        output[category].sort(key=lambda r: (r["selected_publication_date"] or "", r["title"]), reverse=True)
    paths = save_output(output, args.out)
    failures = sum(c[source]["status"] in ("error", "partial") for c in output["coverage"] for source in sources)
    print(json.dumps({"json": str(paths[0]), "csv": str(paths[1]),
                      "counts": {key: len(output[key]) for key in BUCKETS},
                      "incomplete_source_checks": failures}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
