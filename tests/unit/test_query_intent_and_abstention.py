from __future__ import annotations

import unicodedata

import pandas as pd
import pytest

from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.data_contracts.retrieval import RetrievalResponse
from packages.retrieval import BM25Index, HybridRetrievalService


@pytest.fixture
def culinary_service() -> HybridRetrievalService:
    rows = [
        {
            "video_id": "v_mam_tom_heavy",
            "author_handle": "koc_hanoi",
            "tiktok_url": "https://www.tiktok.com/@koc_hanoi/video/v_mam_tom_heavy",
            "play_count": 120000,
            "viral_multiplier": 1.5,
            "engagement_rate": 0.08,
            "has_transcript": True,
            "video_format": "Review quán ăn",
            "food_category": "Món nước & Sợi",
            "dishes": ["bún đậu"],
            "city_norm": "hà nội",
            "district_norm": "quận đống đa",
            "region": "north",
            "poi_name": "Bún đậu Hàng Khay",
            "price_tier": "budget",
            "occasions": ["an_trua"],
            "duration_sec": 40,
            "duration_bucket": "short_20_45s",
            "hook_text": "Mẹt bún đậu mắm tôm đậm đặc sủi bọt siêu nặng mùi!",
            "body_beats": ["Mắm tôm pha chanh ớt cay xè", "Chả cốm nóng giòn"],
            "cta_text": "Ghé thử nha",
            "caption": "Review bún đậu mắm tôm siêu đậm đặc Hà Nội",
            "transcript": "Mẹt bún đậu mắm tôm đậm đặc mắm tôm pha tắc cay nồng, ai mê mắm tôm phải thử.",
            "rag_document": (
                "[Review quán ăn | Món nước & Sợi | budget] Món: bún đậu. Địa điểm: hà nội. "
                "Caption: Review bún đậu mắm tôm siêu đậm đặc Hà Nội "
                "Transcript: Mẹt bún đậu mắm tôm đậm đặc mắm tôm pha tắc cay nồng, ai mê mắm tôm phải thử."
            ),
        },
        {
            "video_id": "v_nuoc_mam_clean",
            "author_handle": "koc_hanoi_2",
            "tiktok_url": "https://www.tiktok.com/@koc_hanoi_2/video/v_nuoc_mam_clean",
            "play_count": 110000,
            "viral_multiplier": 1.4,
            "engagement_rate": 0.07,
            "has_transcript": True,
            "video_format": "Review quán ăn",
            "food_category": "Món nước & Sợi",
            "dishes": ["bún đậu"],
            "city_norm": "hà nội",
            "district_norm": "quận cầu giấy",
            "region": "north",
            "poi_name": "Bún đậu Cầu Giấy",
            "price_tier": "budget",
            "occasions": ["an_trua"],
            "duration_sec": 38,
            "duration_bucket": "short_20_45s",
            "hook_text": "Đi ăn bún đậu chấm nước mắm tỏi ớt thanh nhẹ!",
            "body_beats": ["Đậu mơ rán giòn", "Thịt chân giò luộc mềm"],
            "cta_text": "Lưu địa chỉ nhé",
            "caption": "Bún đậu chấm nước mắm cho team thanh đạm Hà Nội",
            "transcript": "Quán bún đậu có pha sẵn chén nước mắm chua ngọt rất vừa miệng, đậu rán giòn rụm.",
            "rag_document": (
                "[Review quán ăn | Món nước & Sợi | budget] Món: bún đậu. Địa điểm: hà nội. "
                "Caption: Bún đậu chấm nước mắm cho team thanh đạm Hà Nội "
                "Transcript: Quán bún đậu có pha sẵn chén nước mắm chua ngọt rất vừa miệng, đậu rán giòn rụm."
            ),
        },
        {
            "video_id": "v_dau_hu_hcm",
            "author_handle": "koc_sg",
            "tiktok_url": "https://www.tiktok.com/@koc_sg/video/v_dau_hu_hcm",
            "play_count": 95000,
            "viral_multiplier": 1.3,
            "engagement_rate": 0.06,
            "has_transcript": True,
            "video_format": "Review món ăn",
            "food_category": "Đồ ngọt, Trà & Cà phê",
            "dishes": ["chè"],
            "city_norm": "hồ chí minh",
            "district_norm": "quận 5",
            "region": "south",
            "poi_name": "Chè Quận 5",
            "price_tier": "budget",
            "occasions": ["an_vat_xe_chieu"],
            "duration_sec": 30,
            "duration_bucket": "short_20_45s",
            "hook_text": "Chén đậu hũ nước đường gừng nóng hổi ở Quận 5",
            "body_beats": ["Đậu hũ mềm mịn tan trong miệng", "Nước đường thanh mát"],
            "cta_text": "Thử ngay nha",
            "caption": "Đậu hũ nước đường gừng Quận 5 Hồ Chí Minh",
            "transcript": "Hôm nay giới thiệu món công thức nấu chè đậu hũ gừng thơm lừng ở Hồ Chí Minh.",
            "rag_document": (
                "[Review món ăn | Đồ ngọt, Trà & Cà phê | budget] Món: chè. Địa điểm: quận 5 - hồ chí minh. "
                "Caption: Đậu hũ nước đường gừng Quận 5 Hồ Chí Minh "
                "Transcript: Hôm nay giới thiệu món công thức nấu chè đậu hũ gừng thơm lừng ở Hồ Chí Minh."
            ),
        },
        {
            "video_id": "v_dalat_cafe",
            "author_handle": "koc_dalat",
            "tiktok_url": "https://www.tiktok.com/@koc_dalat/video/v_dalat_cafe",
            "play_count": 80000,
            "viral_multiplier": 1.2,
            "engagement_rate": 0.05,
            "has_transcript": True,
            "video_format": "Review quán ăn",
            "food_category": "Đồ ngọt, Trà & Cà phê",
            "dishes": ["cà phê"],
            "city_norm": "đà lạt",
            "district_norm": None,
            "region": "south",
            "poi_name": "Tiệm Cà Phê Đồi Thông",
            "price_tier": "mid",
            "occasions": ["hen_ho"],
            "duration_sec": 35,
            "duration_bucket": "short_20_45s",
            "hook_text": "Quán cà phê săn mây buổi sáng ở Đà Lạt",
            "body_beats": ["Bánh sừng bò nướng thơm", "Cà phê kem béo"],
            "cta_text": "Lên Đà Lạt nhớ ghé",
            "caption": "Review quán cà phê bánh ngọt đẹp ở Đà Lạt",
            "transcript": "Buổi sáng uống cà phê ngắm thông ở Đà Lạt cực chill, bánh ngọt mới nướng.",
            "rag_document": (
                "[Review quán ăn | Đồ ngọt, Trà & Cà phê | mid] Món: cà phê. Địa điểm: đà lạt. "
                "Caption: Review quán cà phê bánh ngọt đẹp ở Đà Lạt "
                "Transcript: Buổi sáng uống cà phê ngắm thông ở Đà Lạt cực chill, bánh ngọt mới nướng."
            ),
        },
    ]
    df = pd.DataFrame(rows)
    bm25 = BM25Index.build(df["video_id"].tolist(), df["rag_document"].tolist(), min_bigram_df=1)
    return HybridRetrievalService(df_videos=df, bm25_index=bm25)


def test_retrieval_response_defaults_remain_backward_compatible() -> None:
    resp = RetrievalResponse(
        query="phở bò",
        mode="bm25",
        reranked=True,
        total_candidates=0,
        relaxed_filters=[],
        items=[],
        timings_ms={"total_ms": 1.2},
    )
    assert resp.insufficient_evidence is False
    assert resp.abstain_reason is None


def test_negation_excludes_positive_boost_and_demotes_violating_doc(
    culinary_service: HybridRetrievalService,
) -> None:
    resp = culinary_service.search(
        RetrievalRequest(query="bún đậu không mắm tôm", mode="bm25", top_k=5, rerank=True)
    )
    assert resp.insufficient_evidence is False
    assert len(resp.items) >= 2
    assert resp.items[0].citation.video_id == "v_nuoc_mam_clean"


def test_nfd_and_nfc_queries_produce_identical_ranking(
    culinary_service: HybridRetrievalService,
) -> None:
    q_nfc = "bún đậu không mắm tôm"
    q_nfd = unicodedata.normalize("NFD", q_nfc)
    assert q_nfc != q_nfd

    resp_nfc = culinary_service.search(RetrievalRequest(query=q_nfc, mode="bm25", top_k=5, rerank=True))
    resp_nfd = culinary_service.search(RetrievalRequest(query=q_nfd, mode="bm25", top_k=5, rerank=True))
    assert [it.citation.video_id for it in resp_nfd.items] == [
        it.citation.video_id for it in resp_nfc.items
    ]
    assert [it.score for it in resp_nfd.items] == [it.score for it in resp_nfc.items]


def test_regional_and_culinary_synonym_expansion_recovers_match(
    culinary_service: HybridRetrievalService,
) -> None:
    # Document only contains "đậu hũ" and "hồ chí minh", while query uses colloquial "tàu hũ Sài Gòn".
    resp = culinary_service.search(
        RetrievalRequest(query="tàu hũ gừng Sài Gòn", mode="bm25", top_k=5, rerank=True)
    )
    assert resp.insufficient_evidence is False
    assert [it.citation.video_id for it in resp.items[:1]] == ["v_dau_hu_hcm"]


@pytest.mark.parametrize(
    "no_answer_query",
    [
        "công thức nấu thịt kangaroo hầm rượu vang",
        "review quán sushi cá nóc fugu chuẩn Nhật",
    ],
)
def test_out_of_corpus_exotic_dish_abstains_without_fabricated_support(
    culinary_service: HybridRetrievalService,
    no_answer_query: str,
) -> None:
    resp = culinary_service.search(
        RetrievalRequest(query=no_answer_query, mode="bm25", top_k=5, rerank=True)
    )
    assert resp.items == []
    assert resp.insufficient_evidence is True
    assert resp.abstain_reason is not None and len(resp.abstain_reason) > 0


def test_strict_city_filter_with_absent_dish_abstains_instead_of_cross_city_fabrication(
    culinary_service: HybridRetrievalService,
) -> None:
    # "bún đậu" exists only in Hà Nội in this fixture; asking for "bún đậu" filtered to Đà Lạt must abstain.
    resp = culinary_service.search(
        RetrievalRequest(
            query="review quán bún đậu ngon",
            mode="bm25",
            top_k=5,
            rerank=True,
            filters=NicheQueryFilter(city_norm="đà lạt"),
        )
    )
    assert resp.items == []
    assert resp.insufficient_evidence is True


def test_broad_location_query_and_all_negated_query_do_not_crash_or_false_abstain(
    culinary_service: HybridRetrievalService,
) -> None:
    broad = culinary_service.search(
        RetrievalRequest(
            query="review quán ăn ngon ở Hồ Chí Minh",
            mode="bm25",
            top_k=5,
            rerank=True,
            filters=NicheQueryFilter(city_norm="hồ chí minh"),
        )
    )
    assert broad.insufficient_evidence is False
    assert len(broad.items) >= 1
    assert broad.items[0].citation.video_id == "v_dau_hu_hcm"

    all_neg = culinary_service.search(
        RetrievalRequest(query="không cay không mắm tôm", mode="bm25", top_k=5, rerank=True)
    )
    assert isinstance(all_neg, RetrievalResponse)
    assert all_neg.items == []
    assert all_neg.insufficient_evidence is True
    assert all_neg.abstain_reason == "query_contains_only_negations"


def test_multi_negation_three_token_negation_and_all_negated_abstention(
    culinary_service: HybridRetrievalService,
) -> None:
    from packages.retrieval import parse_query_intent

    only_neg = parse_query_intent("không cay không mắm tôm")
    assert only_neg.positive_query == ""
    assert only_neg.negated_terms == ("cay", "mắm tôm")

    multi = parse_query_intent("bún bò ghét hành không ngò bỏ nước cốt dừa trừ ớt")
    assert multi.positive_query == "bún bò"
    assert multi.negated_terms == ("hành", "ngò", "nước cốt dừa", "ớt")
    flat_anchors = {phrase for grp in multi.anchor_groups for phrase in grp}
    assert flat_anchors.isdisjoint({"không", "ngò", "dừa", "ớt", "hành"})

    diet = parse_query_intent("thực đơn ăn kiêng ít calo không dầu mỡ")
    assert "ăn kiêng" in diet.positive_query
    assert "ít calo" in diet.positive_query
    assert diet.negated_terms == ("dầu mỡ",)

    resp = culinary_service.search(
        RetrievalRequest(query="không mắm tôm", mode="bm25", top_k=5, rerank=True)
    )
    assert resp.items == []
    assert resp.insufficient_evidence is True
    assert resp.abstain_reason == "query_contains_only_negations"


def test_in_vocab_dish_with_oov_venue_name_does_not_false_abstain_while_exotic_dish_abstains(
    culinary_service: HybridRetrievalService,
) -> None:
    valid_new_shop = culinary_service.search(
        RetrievalRequest(
            query="review quán bún đậu Bếp Kiênz ở Hà Nội",
            mode="bm25",
            top_k=5,
            rerank=True,
        )
    )
    assert valid_new_shop.insufficient_evidence is False
    assert len(valid_new_shop.items) >= 2
    assert {it.citation.video_id for it in valid_new_shop.items}.issuperset(
        {"v_nuoc_mam_clean", "v_mam_tom_heavy"}
    )

    for exotic in (
        "cách làm bánh haggis truyền thống Scotland",
        "review quán bánh quesadilla phô mai",
        "hướng dẫn chế biến escargot ốc sên Pháp",
        "review nhà hàng sashimi cá nóc fugu",
        "công thức nấu thịt kangaroo hầm rượu vang đỏ",
    ):
        abstained = culinary_service.search(
            RetrievalRequest(
                query=exotic,
                mode="bm25",
                top_k=5,
                rerank=True,
                filters=NicheQueryFilter(video_format="Hướng dẫn nấu ăn"),
            )
        )
        assert abstained.items == [], exotic
        assert abstained.insufficient_evidence is True, exotic
        assert "lexical_fallback_unfiltered" not in abstained.relaxed_filters, exotic


def test_reranker_negation_uses_word_boundaries_and_exempts_dietary_accommodation() -> None:
    from packages.retrieval.rerank.scorer import EvidenceReranker

    reranker = EvidenceReranker(enabled=True)
    lookup = {
        "v_substr_safe": {
            "caption": "Lẩu nấm các loại rau cách nấu cái nồi",
            "poi_name": "Thành phố Hồ Chí Minh chi nhánh 1",
            "hook_text": "Lẩu nấm thanh ngọt",
            "dishes": ["lẩu"],
            "price_tier": "budget",
            "occasions": [],
            "body_beats": ["Nấm tươi", "Nước ngọt"],
            "viral_multiplier": 1.0,
            "transcript": "Lẩu nấm các loại rau tại thành phố rất ngon.",
        },
        "v_baseline_clean": {
            "caption": "Lẩu nấm tươi sạch ngon lành tại nhà",
            "poi_name": "Quán Nấm Quận 1",
            "hook_text": "Lẩu nấm thanh ngọt",
            "dishes": ["lẩu"],
            "price_tier": "budget",
            "occasions": [],
            "body_beats": ["Nấm tươi", "Nước ngọt"],
            "viral_multiplier": 1.0,
            "transcript": "Lẩu nấm tươi sạch ngon lành rất vừa miệng.",
        },
        "v_real_fish": {
            "caption": "Lẩu nấm cá hồi tươi ngon đậm vị",
            "poi_name": "Quán Nấm Quận 1",
            "hook_text": "Lẩu nấm thanh ngọt",
            "dishes": ["lẩu"],
            "price_tier": "budget",
            "occasions": [],
            "body_beats": ["Nấm tươi", "Nước ngọt"],
            "viral_multiplier": 1.0,
            "transcript": "Lẩu nấm cá hồi tươi ngon rất vừa miệng.",
        },
        "v_accommodates": {
            "caption": "Review bún đậu chấm nước mắm",
            "poi_name": "Bún Đậu Ngõ Nhỏ",
            "hook_text": "Mẹt bún đậu nóng giòn",
            "dishes": ["bún đậu"],
            "price_tier": "budget",
            "occasions": [],
            "body_beats": ["Đậu giòn", "Thịt luộc"],
            "viral_multiplier": 1.0,
            "transcript": "Quán bún đậu có nước mắm cho bạn nào không ăn được mắm tôm và không cho hành.",
        },
        "v_no_mention": {
            "caption": "Review bún đậu chấm nước mắm",
            "poi_name": "Bún Đậu Ngõ Nhỏ",
            "hook_text": "Mẹt bún đậu nóng giòn",
            "dishes": ["bún đậu"],
            "price_tier": "budget",
            "occasions": [],
            "body_beats": ["Đậu giòn", "Thịt luộc"],
            "viral_multiplier": 1.0,
            "transcript": "Quán bún đậu có nước mắm chua ngọt thanh đạm rất vừa miệng.",
        },
    }

    scored_fish = dict(
        (vid, score)
        for vid, score, _ in reranker.rerank(
            query="lẩu nấm thanh ngọt",
            candidates=[("v_substr_safe", 1.0), ("v_baseline_clean", 1.0), ("v_real_fish", 1.0)],
            video_lookup=lookup,
            top_k=5,
            negated_terms=("cá", "hành"),
        )
    )
    assert scored_fish["v_substr_safe"] == pytest.approx(scored_fish["v_baseline_clean"], abs=1e-5)
    assert scored_fish["v_real_fish"] == pytest.approx(scored_fish["v_baseline_clean"] - 0.25, abs=1e-5)

    scored_bd = dict(
        (vid, score)
        for vid, score, _ in reranker.rerank(
            query="bún đậu nước mắm",
            candidates=[("v_accommodates", 1.0), ("v_no_mention", 1.0)],
            video_lookup=lookup,
            top_k=5,
            negated_terms=("mắm tôm", "hành"),
        )
    )
    assert scored_bd["v_accommodates"] == pytest.approx(scored_bd["v_no_mention"], abs=1e-5)


def test_dense_and_hybrid_rrf_enforce_query_normalization_and_no_answer_abstention() -> None:
    from packages.retrieval.dense.encoder import TruncatedSvdDenseEncoder
    from packages.retrieval.dense.local_index import LocalDenseIndex

    docs = [
        "bún bò huế nước dùng đậm đà sả thơm ngon",
        "tô bún bò tái nạm chả cua huế chuẩn vị thanh ngọt",
        "phở bò tái chín hà nội nước lèo thanh ngọt",
        "cơm tấm sườn bì chả trứng ốp la sài gòn",
        "bún đậu mắm tôm chả cốm nem chua rán giòn",
        "gà rán sốt cay hàn quốc giòn tan cùng phô mai",
    ]
    vids = [f"vd_{i}" for i in range(len(docs))]
    df = pd.DataFrame(
        [
            {
                "video_id": vid,
                "author_handle": f"c_{i}",
                "tiktok_url": f"https://www.tiktok.com/@c_{i}/video/{vid}",
                "play_count": 10000,
                "viral_multiplier": 1.2,
                "engagement_rate": 0.05,
                "has_transcript": True,
                "video_format": "Review món ăn",
                "food_category": "Món nước & Sợi",
                "dishes": [],
                "city_norm": "hồ chí minh",
                "district_norm": None,
                "region": "south",
                "poi_name": None,
                "price_tier": "budget",
                "occasions": [],
                "duration_sec": 30,
                "duration_bucket": "short_20_45s",
                "hook_text": doc,
                "body_beats": [doc],
                "cta_text": "",
                "caption": doc,
                "transcript": doc,
                "rag_document": doc,
            }
            for i, (vid, doc) in enumerate(zip(vids, docs))
        ]
    )
    bm25 = BM25Index.build(vids, docs, min_bigram_df=1)
    enc = TruncatedSvdDenseEncoder.fit(docs, dimension=4)
    dense = LocalDenseIndex.build(vids, enc.encode_documents(docs), model_id=enc.model_id)
    svc = HybridRetrievalService(df_videos=df, bm25_index=bm25, dense_index=dense, dense_encoder=enc)

    for mode in ("bm25", "dense", "hybrid_rrf"):
        no_ans = svc.search(
            RetrievalRequest(
                query="công thức nấu thịt kangaroo hầm rượu vang đỏ",
                mode=mode,
                top_k=3,
                rerank=True,
            )
        )
        assert no_ans.items == [], mode
        assert no_ans.insufficient_evidence is True, mode

        q_nfc = "bún bò huế không cay"
        q_nfd = unicodedata.normalize("NFD", q_nfc)
        r_nfc = svc.search(RetrievalRequest(query=q_nfc, mode=mode, top_k=3, rerank=True))
        r_nfd = svc.search(RetrievalRequest(query=q_nfd, mode=mode, top_k=3, rerank=True))
        assert r_nfc.insufficient_evidence is False, mode
        assert [x.citation.video_id for x in r_nfc.items] == [
            x.citation.video_id for x in r_nfd.items
        ], mode
        assert r_nfc.items[0].citation.video_id in {"vd_0", "vd_1"}, mode


def test_noisy_machine_dish_tag_without_text_evidence_is_filtered_out() -> None:
    rows = [
        {
            "video_id": "v_noisy_xoi",
            "author_handle": "koc_xoi",
            "tiktok_url": "https://www.tiktok.com/@koc_xoi/video/v_noisy_xoi",
            "play_count": 500000,
            "viral_multiplier": 8.0,
            "engagement_rate": 0.1,
            "has_transcript": True,
            "video_format": "Mukbang",
            "food_category": "Cơm & Bữa chính",
            "dishes": ["bún đậu"],  # Spurious legacy machine tag
            "city_norm": None,
            "district_norm": None,
            "region": "unknown",
            "poi_name": None,
            "price_tier": "budget",
            "occasions": [],
            "duration_sec": 35,
            "duration_bucket": "short_20_45s",
            "hook_text": "Ăn xôi cục thịt kho bự đi",
            "body_beats": ["Xôi vừa dẻo vừa thơm"],
            "cta_text": "",
            "caption": "Xôi thịt kho nước mắm siêu ngon",
            "transcript": "Ăn xôi cục thịt kho nước mắm vừa dẻo vừa thơm.",
            "rag_document": "[Mukbang] Món: bún đậu. Caption: Xôi thịt kho nước mắm Transcript: Ăn xôi cục thịt kho.",
        },
        {
            "video_id": "v_real_bun_dau",
            "author_handle": "koc_bd",
            "tiktok_url": "https://www.tiktok.com/@koc_bd/video/v_real_bun_dau",
            "play_count": 50000,
            "viral_multiplier": 1.1,
            "engagement_rate": 0.05,
            "has_transcript": True,
            "video_format": "Review quán ăn",
            "food_category": "Món nước & Sợi",
            "dishes": ["bún đậu"],
            "city_norm": "hà nội",
            "district_norm": None,
            "region": "north",
            "poi_name": "Bún Đậu Ngõ Nhỏ",
            "price_tier": "budget",
            "occasions": [],
            "duration_sec": 35,
            "duration_bucket": "short_20_45s",
            "hook_text": "Mẹt bún đậu chấm nước mắm tỏi ớt",
            "body_beats": ["Đậu rán nóng hổi"],
            "cta_text": "",
            "caption": "Review bún đậu chấm nước mắm Hà Nội",
            "transcript": "Hôm nay ăn bún đậu chấm nước mắm cho bạn nào không ăn được mắm tôm.",
            "rag_document": "[Review quán ăn] Món: bún đậu. Caption: Review bún đậu chấm nước mắm Transcript: Hôm nay ăn bún đậu chấm nước mắm.",
        },
    ]
    df = pd.DataFrame(rows)
    bm25 = BM25Index.build(df["video_id"].tolist(), df["rag_document"].tolist(), min_bigram_df=1)
    svc = HybridRetrievalService(df_videos=df, bm25_index=bm25)

    resp = svc.search(
        RetrievalRequest(query="bún đậu chấm nước mắm không mắm tôm", mode="bm25", top_k=5, rerank=True)
    )
    assert resp.items[0].citation.video_id == "v_real_bun_dau"
    assert "v_noisy_xoi" not in [it.citation.video_id for it in resp.items]


def test_reindeer_cake_decoration_does_not_fabricate_reindeer_meat_support() -> None:
    rows = [
        {
            "video_id": "v_xmas_cake",
            "author_handle": "pastry_shop",
            "tiktok_url": "https://www.tiktok.com/@pastry_shop/video/v_xmas_cake",
            "play_count": 90000,
            "viral_multiplier": 1.5,
            "engagement_rate": 0.06,
            "has_transcript": True,
            "video_format": "Review món ăn",
            "food_category": "Đồ ngọt, Trà & Cà phê",
            "dishes": ["bánh ngọt"],
            "city_norm": "hồ chí minh",
            "district_norm": None,
            "region": "south",
            "poi_name": "Tiệm Bánh Giáng Sinh",
            "price_tier": "mid",
            "occasions": [],
            "duration_sec": 30,
            "duration_bucket": "short_20_45s",
            "hook_text": "Bánh kem Giáng sinh hình tuần lộc dễ thương",
            "body_beats": ["Cốt bánh chocolate mềm"],
            "cta_text": "",
            "caption": "Ăn bánh Giáng sinh Bắc Âu tuần lộc sớm",
            "transcript": "Bộ sưu tập bánh Giáng sinh Bắc Âu hình tuần lộc và ông già Noel rất xinh xắn.",
            "rag_document": "Ăn bánh Giáng sinh Bắc Âu hình tuần lộc nướng thơm phức",
        }
    ]
    df = pd.DataFrame(rows)
    bm25 = BM25Index.build(df["video_id"].tolist(), df["rag_document"].tolist(), min_bigram_df=1)
    svc = HybridRetrievalService(df_videos=df, bm25_index=bm25)

    resp = svc.search(
        RetrievalRequest(query="review quán thịt tuần lộc nướng Bắc Âu", mode="bm25", top_k=5, rerank=True)
    )
    assert resp.items == []
    assert resp.insufficient_evidence is True

