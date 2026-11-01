import unittest
from scripts.research_batch import article_metadata

class ArticleMetadataTests(unittest.TestCase):
    def test_article_jsonld_precedes_event_time(self):
        body='<html lang="ja"><time datetime="2026-11-06T19:00:00+09:00">イベント</time><script type="application/ld+json">{"@type":"BlogPosting","datePublished":"2026-10-31T10:14:29.440Z"}</script></html>'
        self.assertEqual(article_metadata(body,'https://example.com/post')['publishedAt'],'2026-10-31T10:14:29.440000Z')
    def test_event_jsonld_does_not_override_article(self):
        body='<script type="application/ld+json">{"@graph":[{"@type":"NewsArticle","datePublished":"2026-10-31T03:00:00Z"},{"@type":"Event","datePublished":"2026-11-06T10:00:00Z"}]}</script>'
        self.assertEqual(article_metadata(body,'https://example.com/post')['publishedAt'],'2026-10-31T03:00:00Z')
    def test_meta_is_independent_of_earlier_time(self):
        body='<time datetime="2026-11-06T10:00:00Z"></time><meta property="article:published_time" content="2026-10-31T03:00:00Z">'
        self.assertEqual(article_metadata(body,'https://example.com/post')['publishedAt'],'2026-10-31T03:00:00Z')
