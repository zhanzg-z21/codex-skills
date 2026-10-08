"""Offline tests for date selection, identity, metadata parsing and coverage."""

import copy
import datetime as dt
import json
import unittest
import xml.etree.ElementTree as ET

import fetch_recent as scout


JOURNAL = {"id": "test", "name": "Example Journal", "pubmed_query": '"Example Journal"[Journal]',
           "issns": ["1234-5678"], "publisher_latest_urls": ["https://example.org/latest"]}
START, END = dt.date(2026, 9, 30), dt.date(2026, 10, 4)


def record(doi="", pmid="", online=None):
    result = scout.empty_record(JOURNAL, "pubmed", pmid, "https://example.org/article", "query")
    result.update(doi=doi, pmids=[pmid] if pmid else [], title="Same title")
    if online:
        result["date_evidence"].append(scout.evidence("pubmed", "online", "ArticleDate", online))
    return result


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = 0
        self.calls = []

    def request(self, url, params, post=False):
        self.requests += 1
        self.calls.append((url, params, post))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return json.dumps(response).encode() if isinstance(response, dict) else response


def crossref_page(items, total, cursor=None):
    return {"status": "ok", "message": {"items": items, "total-results": total, "next-cursor": cursor}}


class DateTests(unittest.TestCase):
    def test_inclusive_window(self):
        for parts in ([2026, 9, 30], [2026, 10, 4]):
            self.assertEqual(scout.classify(record(online=parts), START, END), "articles")

    def test_old_online_recent_print_is_not_new(self):
        item = record(online=[2026, 8, 1])
        item["date_evidence"] += [scout.evidence("pubmed", "print", "issue", [2026, 10, 1]),
                                  scout.evidence("pubmed", "created", "entrez", [2026, 10, 2])]
        self.assertEqual(scout.classify(item, START, END), "late_indexed")
        self.assertEqual(item["selected_publication_date"], "2026-08-01")

    def test_conflicting_online_dates(self):
        item = record(online=[2026, 10, 1])
        item["date_evidence"].append(scout.evidence("crossref", "online", "published-online", [2026, 10, 2]))
        self.assertEqual(scout.classify(item, START, END), "date_uncertain")

    def test_partial_date_not_imputed(self):
        item = record(online=[2026, 10])
        self.assertEqual(scout.classify(item, START, END), "date_uncertain")
        self.assertEqual(item["date_evidence"][0]["value"], "2026-10")

    def test_partial_date_consistent_with_exact(self):
        item = record(online=[2026, 10])
        item["date_evidence"].append(scout.evidence("crossref", "online", "published-online", [2026, 10, 2]))
        self.assertEqual(scout.classify(item, START, END), "articles")

    def test_print_only_needs_online_verification(self):
        item = record()
        item["date_evidence"].append(scout.evidence("pubmed", "print", "issue", [2026, 10, 2]))
        self.assertEqual(scout.classify(item, START, END), "date_uncertain")

    def test_missing_and_future_dates(self):
        self.assertEqual(scout.classify(record(), START, END), "date_uncertain")
        self.assertEqual(scout.classify(record(online=[2026, 10, 5]), START, END), "outside_window")

    def test_invalid_and_range_months(self):
        self.assertEqual(scout.date_value([2026, 2, 30]), (None, "unknown"))
        self.assertEqual(scout.date_value([2026, None, 5]), (None, "unknown"))
        node = ET.fromstring("<PubDate><Year>2026</Year><Month>Sep-Oct</Month></PubDate>")
        self.assertEqual(scout.xml_date(node, "issue", "PubDate")["precision"], "unknown")


class IdentityTests(unittest.TestCase):
    def test_doi_merges_and_retains_date_sources(self):
        first, second = record("10.1/a", "1", [2026, 10, 1]), record("10.1/a", "", [2026, 10, 1])
        second["date_evidence"][0]["source"] = "crossref"
        second["retrieval_sources"][0]["source"] = "crossref"
        merged = scout.deduplicate([first, second])
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0]["date_evidence"]), 2)
        self.assertEqual(len(merged[0]["retrieval_sources"]), 2)

    def test_title_does_not_merge(self):
        self.assertEqual(len(scout.deduplicate([record("10.1/a"), record("10.1/b")])), 2)
        self.assertEqual(len(scout.deduplicate([record(), record()])), 2)

    def test_pmid_fallback(self):
        merged = scout.deduplicate([record("", "1"), record("10.1/a", "1")])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["doi"], "10.1/a")

    def test_conflicting_doi_is_not_merged_by_pmid(self):
        merged = scout.deduplicate([record("10.1/a", "1"), record("10.1/b", "1"), record("", "1")])
        self.assertEqual(len(merged), 3)
        self.assertTrue(all(r["metadata_warnings"] for r in merged))


class RetrievalTests(unittest.TestCase):
    def test_query_contains_all_date_fields_without_topic_filter(self):
        query = scout.pubmed_query(JOURNAL, START, END)
        self.assertEqual(query, '("Example Journal"[Journal]) AND (2026/09/30:2026/10/04[dp] OR 2026/09/30:2026/10/04[epdat] OR 2026/09/30:2026/10/04[crdt])')

    def test_pubmed_xml_metadata(self):
        data = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>42</PMID>
        <Article PubModel="Print-Electronic"><ArticleTitle>A <i>test</i> title</ArticleTitle>
        <Journal><JournalIssue><PubDate><Year>2026</Year><Month>Oct</Month></PubDate></JournalIssue></Journal>
        <ArticleDate DateType="Electronic"><Year>2026</Year><Month>09</Month><Day>30</Day></ArticleDate>
        <Abstract><AbstractText Label="RESULTS">Some finding.</AbstractText></Abstract>
        <PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType></PublicationTypeList>
        </Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/ABC</ArticleId></ArticleIdList>
        <History><PubMedPubDate PubStatus="entrez"><Year>2026</Year><Month>10</Month><Day>2</Day></PubMedPubDate></History>
        </PubmedData></PubmedArticle></PubmedArticleSet>'''
        item = scout.parse_pubmed(data, JOURNAL, "query")[0]
        self.assertEqual(item["doi"], "10.1/abc")
        self.assertEqual(item["title"], "A test title")
        self.assertEqual(item["abstract"], "RESULTS: Some finding.")
        self.assertIn("Randomized Controlled Trial", item["publication_types"])
        self.assertEqual(scout.classify(item, START, END), "articles")

    def test_crossref_pages_and_correct_filter(self):
        items = [{"DOI": "10.1/" + str(i), "published-online": {"date-parts": [[2026, 10, 1]]}}
                 for i in range(3)]
        client = FakeClient([crossref_page(items[:2], 3, "cursor1"), crossref_page(items[2:], 3)])
        records, coverage = scout.fetch_crossref(JOURNAL, START, END, client, rows=2)
        self.assertEqual(len(records), 3)
        self.assertEqual(coverage["status"], "ok")
        self.assertEqual(client.calls[1][1]["cursor"], "cursor1")
        self.assertEqual(client.calls[0][1]["filter"], "from-online-pub-date:2026-09-30,until-online-pub-date:2026-10-04")

    def test_crossref_partial_keeps_retrieved_records(self):
        client = FakeClient([crossref_page([{"DOI": "10.1/a"}], 2, "cursor1"), RuntimeError("HTTP 503")])
        records, coverage = scout.fetch_crossref(JOURNAL, START, END, client, rows=1)
        self.assertEqual(len(records), 1)
        self.assertEqual(coverage["status"], "partial")
        self.assertIn("HTTP 503", coverage["errors"][0])

    def test_crossref_repeated_page_is_partial(self):
        page = crossref_page([{"DOI": "10.1/a"}], 3, "cursor1")
        records, coverage = scout.fetch_crossref(JOURNAL, START, END, FakeClient([page, page]), rows=1)
        self.assertEqual(len(records), 1)
        self.assertEqual(coverage["status"], "partial")

    def test_zero_results_differ_from_failure(self):
        empty = FakeClient([{"esearchresult": {"count": "0", "idlist": []}}])
        records, coverage = scout.fetch_pubmed(JOURNAL, START, END, empty)
        self.assertEqual(records, [])
        self.assertEqual(coverage["status"], "ok")
        self.assertEqual(coverage["expected_count"], 0)
        records, coverage = scout.fetch_pubmed(JOURNAL, START, END, FakeClient([RuntimeError("HTTP 503")]))
        self.assertEqual(coverage["status"], "error")
        self.assertIsNone(coverage["expected_count"])
        records, coverage = scout.fetch_crossref(JOURNAL, START, END, FakeClient([crossref_page([], 0)]))
        self.assertEqual(coverage["status"], "ok")
        self.assertEqual(coverage["expected_count"], 0)


if __name__ == "__main__":
    unittest.main()
