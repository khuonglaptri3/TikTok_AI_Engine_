"""Apply K's 65-item blinded full-transcript audit and run M4.2 v2 leakage-free verification."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

import pandas as pd

from packages.absa.disclosure import (
    FORBIDDEN_DISCLOSURE_HASHTAGS,
    extract_promotional_indicators,
)
from packages.absa.disclosure_eval import (
    compute_pu_observable_summary,
    evaluate_observed_ad_vs_ec_classifier,
    strip_forbidden_inline_hashtags,
)
from packages.analytics import load_verified_corpus
from packages.common.resources import get_peak_rss_mib


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


K_BLINDED_JUDGMENTS: dict[str, tuple[str, str]] = {
    "m4_2_001": ("brand_or_venue_focus_no_cta", "Dedicated mukbang challenge naming @Ba Vì Farm milk cakes (3 flavors); regex 'mua ngay' is creator first-person ('chơi lớn mua ngay 100 cái'), no viewer cart/discount CTA."),
    "m4_2_002": ("explicit_promo_cta", "Explicit time-limited venue promo at Buffet Nhà Tui Tân Phú: 79k reduced to 69k until Dec 15 plus free nghêu sốt bơ cay upon check-in."),
    "m4_2_003": ("organic_or_general_review", "Home-cooking tutorial for 3 dipping sauces (muối ớt xanh/đỏ, chanh dây) with zero brand, venue, or commercial CTA."),
    "m4_2_004": ("unclear_or_noisy_text", "ASR transcribed background wedding pop-song lyrics ('Hôm nay em bắt anh làm chồng...') instead of speech; caption only names home dish chả cá quết bánh ram."),
    "m4_2_005": ("brand_or_venue_focus_no_cta", "Single-brand product praise for ChinSu 4-flavor dipping salt pack ('combo muối chấm tứ vị ChinSu'); 'combo' denotes product set without explicit cart link or discount."),
    "m4_2_006": ("organic_or_general_review", "Instant-noodle and generic Russian-style beef tendon sausage mukbang with no brand name, venue, or shop CTA."),
    "m4_2_007": ("brand_or_venue_focus_no_cta", "Single street-stall spotlight (gánh bánh tráng trộn chị Thủy, Ngô Tất Tố, Bình Thạnh, 20k-50k, #vtmgr) with zero voucher or cart CTA."),
    "m4_2_008": ("brand_or_venue_focus_no_cta", "Dedicated Christmas cake mukbang repeatedly naming bakery brand Pema/Prima (#pema) with zero price, discount, or buy-link CTA."),
    "m4_2_009": ("explicit_promo_cta", "No transcript, but caption and campaign hashtag (#taudautantanrinhquaiphone, '200k đổi lấy điện thoại') explicitly pitch Tân Tân peanut iPhone prize promotion."),
    "m4_2_010": ("explicit_promo_cta", "Full 3,155-char live-style pitch combining restaurant delivery (71 Tân Triều, 140k/dish), out-of-domain 140k puffer jacket TikTok Shop CTA ('ấn vào giỏ hàng', 'free ship'), and paid cooking lessons."),
    "m4_2_011": ("explicit_promo_cta", "Venue promo review for Bee Buk (171 Quan Hoa) pitching 'giá chỉ 139 cành không phụ thu' plus complimentary tokbokki hotpot ('được tặng lẩu tok')."),
    "m4_2_012": ("brand_or_venue_focus_no_cta", "Caption-only single-restaurant spotlight (#larbthai on Nguyễn Gia Trí, Bình Thạnh) with missing transcript and no explicit voucher or booking CTA."),
    "m4_2_013": ("unclear_or_noisy_text", "Missing transcript and 6-word caption ('Lòng Hoa Bằng ngày mát dời') provide insufficient text to verify specific venue branding or promotional cues."),
    "m4_2_014": ("explicit_promo_cta", "Caption-only TikTok Shop cart reference ('Một giỏ hàng toàn là ớt') paired with #tuongotchinsu brand tag."),
    "m4_2_015": ("brand_or_venue_focus_no_cta", "Out-of-domain non-F&B neck massager endorsement (#maymassage #bomidivietnam) in creator feed; caption-only brand recommendation without explicit cart/discount CTA."),
    "m4_2_016": ("brand_or_venue_focus_no_cta", "Caption-only Hanoi vegetarian venue mention (#vegito) with missing transcript and no discount or booking CTA."),
    "m4_2_017": ("organic_or_general_review", "Caption-only generic bánh tráng phơi sương mukbang invitation with no brand, shop, or venue mention."),
    "m4_2_018": ("brand_or_venue_focus_no_cta", "Multi-percentage dark chocolate taste test naming brand Yikanong in caption with mixed/candid bitterness reactions and zero cart or promo CTA."),
    "m4_2_019": ("organic_or_general_review", "Caption-only home-cooked fried rice post ('Cơm nhà ín' matching handle @comnhain) with no commercial cue."),
    "m4_2_020": ("explicit_promo_cta", "Full 2,842-char transcript (beyond 600-char excerpt) reveals explicit bundle gift ('Mua hai hũ... tặng thêm một chai muối chanh') and TikTok Shop cart CTA ('bấm vào giỏ hàng bên dưới') for #79food dried squid."),
    "m4_2_021": ("unclear_or_noisy_text", "ASR captured 100% background pop-song lyrics ('Baby chill out...') while caption gives only generic street-BBQ mood without venue name."),
    "m4_2_022": ("organic_or_general_review", "Caption-only cheap street-food observation ('5ka/ gói xôi đầy ụ ở giữa lòng Phố Cổ', #vtmgr) with no named shop, address, or commercial CTA."),
    "m4_2_023": ("explicit_promo_cta", "Uses live-commerce SKU phrasing ('Mã khô cá dứa bàn tay') and shop freebie pitch ('Được tặng kèm mắm tắc... mắm me của shop')."),
    "m4_2_024": ("organic_or_general_review", "Casual Mekong Delta home meal eating dried fish with watermelon and fruit; zero brand or venue cues."),
    "m4_2_025": ("explicit_promo_cta", "Out-of-domain non-F&B underarm antiperspirant review; full 1,614-char transcript ends with explicit cart CTA ('mình sẽ gắn giỏ hàng trong cái video này')."),
    "m4_2_026": ("brand_or_venue_focus_no_cta", "Caption-only recommendation to buy Thai hotpot broth from named restaurant Khrua Baan Thai for Tết, without price/voucher/cart CTA."),
    "m4_2_027": ("unclear_or_noisy_text", "Missing transcript with 3-word reply caption ('Chải nước mínnn') and #vulaci hashtag; too sparse to classify wording."),
    "m4_2_028": ("organic_or_general_review", "Personal solo birthday vlog boiling 4 sea crabs and lighting a small cake (2,550 chars); zero commercial brand or venue."),
    "m4_2_029": ("organic_or_general_review", "Caption-only homemade jujube milk snack post ('nhà làm dễ ẹt') with no brand or shop cue."),
    "m4_2_030": ("unclear_or_noisy_text", "Missing transcript with 6-word clickbait question ('Nem Tôm làm bằng bìa cát tông?!'); insufficient text to determine brand or review stance."),
    "m4_2_066": ("explicit_promo_cta", "Explicit prize-draw bundle pitch for 'Combo vô đối của nhà bà Tuyết' (#tamcaybatuyet) urging viewers to buy combo for a chance to win SH motorbike/iPhone/gold."),
    "m4_2_067": ("brand_or_venue_focus_no_cta", "Dedicated Hanoi dessert shop review (Caramen 29/31 Hàng Than, 8k/cup, #vtmgr) with zero discount or cart CTA."),
    "m4_2_068": ("explicit_promo_cta", "Explicit TikTok Shop cart CTA ('nhắn vào giỏ hàng', 'Tôi có gắn ở giỏ hàng á') pitching 100k 4-box Nem Thanh Sơn Lai Vung combo."),
    "m4_2_069": ("explicit_promo_cta", "Grand-opening venue promo for Hútt Tea Phú Nhuận pitching 'mua 1 tặng 1' and 100 free cups/day plus 'giá chỉ từ 5.000'."),
    "m4_2_070": ("unclear_or_noisy_text", "Out-of-domain non-F&B handheld electric fan post with missing transcript and 9-word caption lacking brand/CTA detail."),
    "m4_2_071": ("organic_or_general_review", "Caption-only Tết bánh chưng post (#ngoafood #vtmgr) with no named seller, price, or commercial CTA."),
    "m4_2_072": ("brand_or_venue_focus_no_cta", "Mid-recipe native product placement pitching 'bánh tráng sốt bò nhà Beo' (#banhnhapeo, 'bestseller của shop', 'mới mua một combo') inside an Ô Thum grilled-chicken cooking video, without explicit cart link."),
    "m4_2_073": ("explicit_promo_cta", "Full 2,077-char transcript reveals co-branded Sprite x GrabFood campaign CTA ('#CangCayCangDa', order spicy dishes on GrabFood to get free Sprite); missed by regex lexicon."),
    "m4_2_074": ("brand_or_venue_focus_no_cta", "Eat-clean review praising Táo Food mì Chũ and describing included gifts (measuring tape, rice cakes, 1200-kcal menu) on 2kg purchase without explicit cart/link CTA."),
    "m4_2_075": ("organic_or_general_review", "Hà Giang travelogue and local smoked-meat / grilled-skewer vlog snippet with zero commercial pitch."),
    "m4_2_076": ("brand_or_venue_focus_no_cta", "Full 1,984-char transcript starts as flan-jelly cooking then pivots after char 650 into a branded FMCG kitchen-cleaner pitch for Sunlight Powerfoam (#SunlightLaubep #5giaySachDauMo)."),
    "m4_2_077": ("organic_or_general_review", "Caption-only praise of golden cheese bread (#LenkycungKhoa #Vtmgr) with missing transcript and no shop/venue name."),
    "m4_2_078": ("brand_or_venue_focus_no_cta", "Porridge-cooking monologue centered on Bear mini slow cooker (#bearvietnamofficial, 9-hour timer, ceramic pot) with no explicit cart/discount CTA."),
    "m4_2_079": ("unclear_or_noisy_text", "Missing transcript and incomplete teaser caption ('Mình thèm ăn nướng, nó thèm sashimi thì…'); POI is AEON Long Biên but text lacks identifiable venue or wording stance."),
    "m4_2_080": ("explicit_promo_cta", "Caption-only product price pitch ('Mỡ ức khô cá dứa giá chỉ 69 cành')."),
    "m4_2_081": ("explicit_promo_cta", "Out-of-domain kitchen-appliance livestream teaser pitching Lock&Lock air fryer/cookers with 'giảm tới 50% kèm quà tặng', 'hàng ngàn cái voucher sốc', and scheduled live time."),
    "m4_2_082": ("organic_or_general_review", "Caption-only generic budget student-rice review hook with missing transcript and no named venue or CTA."),
    "m4_2_083": ("organic_or_general_review", "Community-support food vlog urging viewers to support an elderly couple's bún mọc stall (2028 Phạm Thế Hiển, Q8, 40k) after loan-shark vandalism; non-commercial empathy/local review."),
    "m4_2_084": ("unclear_or_noisy_text", "Missing transcript with cryptic 4-word caption ('Lại tới nữa rồi 🤣 #emartphanhuyich')."),
    "m4_2_085": ("unclear_or_noisy_text", "ASR transcribed romantic background song lyrics ('Dành hết nữa của đời...') while caption provides an organic home-cooking grilled-oyster dipping-sauce recipe."),
    "m4_2_086": ("unclear_or_noisy_text", "ASR transcribed 100% romantic pop-song lyrics ('Trước khi gặp em và anh sẽ nói I miss you...') over a casual bún chả question caption."),
    "m4_2_087": ("brand_or_venue_focus_no_cta", "Detailed 2,885-char restaurant review of Phở gà 17 Văn Miếu (40k-120k, Ocean Park 2nd branch) with balanced taste critique; regex 'menu' hit is purely descriptive menu-price reporting."),
    "m4_2_088": ("organic_or_general_review", "3,452-char personal life/travel/pregnancy monologue over a bowl of bún bò chả cua with zero commercial mentions."),
    "m4_2_089": ("explicit_promo_cta", "Explicit TikTok Shop pitch for crispy pork lard ('Combo thế này chỉ có 99 cành', 'Free ship luôn', 'Click cửa hàng ngay nha')."),
    "m4_2_090": ("organic_or_general_review", "Caption-only rainy-day solo Samyang spicy-noodle mukbang post with no commercial CTA."),
    "m4_2_091": ("unclear_or_noisy_text", "Missing transcript and 5-word generic caption ('Phần 13 | Dẻo dẻo thơm thơm') without identifiable dish or brand."),
    "m4_2_092": ("brand_or_venue_focus_no_cta", "Dedicated 1,589-char unboxing and taste review of Xù Lèo 15-day wind-dried persimmons (#hongtreogioxuleo, ~10k/fruit) with no cart link or discount CTA."),
    "m4_2_093": ("unclear_or_noisy_text", "ASR captured Korean K-pop background lyrics ('되었다던 건지...') while caption mentions an unnamed Tây Hồ late-night BBQ buffet (regex hit 'buffet')."),
    "m4_2_094": ("explicit_promo_cta", "Mukbang of Hằng Du Mục spicy noodles containing explicit cart CTA ('giờ hang [giỏ hàng] mình có gắn ở phía dưới anh em ơi') missed by regex due to ASR typo 'giờ hang'."),
    "m4_2_095": ("brand_or_venue_focus_no_cta", "Full 2,813-char transcript starts with baguette recipe then devotes >2,000 chars after char 850 to pitching #kochivietnam tabletop dishwasher (>5M VND) without explicit cart link."),
    "m4_2_096": ("brand_or_venue_focus_no_cta", "Dipping-snack challenge culminating in branded Chupa Chups chili-salt lollipop launch segment (#ChupaChups #ChamChamMut) without explicit cart/discount CTA."),
    "m4_2_097": ("explicit_promo_cta", "Full 1,490-char mukbang of #kashay caramel bread crumbs and coffee cookies ending at char ~1,350 with explicit cart CTA ('Mua thì mình để ở góc trái màn hình ấy')."),
    "m4_2_098": ("unclear_or_noisy_text", "ASR transcribed 960 chars of Vietnamese pop-song lyrics ('Thương em lâu rồi từ ngày em tươi như ma non...') over a short 'Chè bơ cùng Nữ' caption."),
    "m4_2_099": ("organic_or_general_review", "Rural comedy cooking skit ('Về Cố Hương Tập 32: Tôm Hùm Nướng Phô Mai') with zero brand or commercial cues."),
    "m4_2_100": ("organic_or_general_review", "Caption-only home-cooked garlic-butter sea snails post (#cooking #monngonmoingay) with no brand or CTA."),
}


def main() -> None:
    repo = Path(__file__).resolve().parents[5]
    corpus_dir = repo / "data/corpus/20261118_taxonomy_fix_v1"
    wb_path = repo / "data/evaluation/m4_2_disclosure/review_sample_100.jsonl"
    llm_path = repo / "data/evaluation/m4_2_disclosure/review_sample_100_llm_draft.jsonl"
    ev_dir = repo / "docs/reports/milestones/M4.2/evidence"
    v2_study_out = repo / "artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json"

    manifest, _, df_videos = load_verified_corpus(corpus_dir)
    tr_lookup = dict(
        zip(df_videos["video_id"].astype(str).tolist(), [str(t or "") for t in df_videos["transcript"].tolist()])
    )

    wb_rows = [json.loads(line) for line in wb_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    llm_rows = {
        json.loads(line)["item_id"]: json.loads(line)
        for line in llm_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    k_audit_rows: list[dict[str, Any]] = []
    n_blinded_rows: list[dict[str, Any]] = []
    updated_wb_rows: list[dict[str, Any]] = []

    k_by_stratum: dict[str, Counter[str]] = {}
    k_vs_llm_agree = 0
    k_vs_llm_diffs: list[dict[str, Any]] = []

    for r in wb_rows:
        iid = str(r["item_id"])
        vid = str(r["video_id"])
        full_tr = tr_lookup.get(vid, str(r.get("transcript_excerpt") or ""))
        rec = dict(r)
        rec["transcript_full"] = full_tr
        # Recompute auto_lexical_promo_indicators using v2 word-boundary/negation-aware matcher
        inds, _, score = extract_promotional_indicators(
            caption=str(rec.get("caption") or ""),
            transcript=full_tr,
            hashtags=list(rec.get("hashtags") or []),
        )
        rec["auto_lexical_promo_indicators"] = inds
        rec["auto_lexical_promo_score"] = score

        # Strictly preserve N_* untouched
        assert rec["N_human_verified"] is False
        assert rec["N_observed_wording_label"] is None

        if rec["review_assignment"] in {"double_review_N_K", "K_only"}:
            lbl, note = K_BLINDED_JUDGMENTS[iid]
            rec["K_observed_wording_label"] = lbl
            rec["K_error_or_domain_note"] = note
            rec["K_human_verified"] = True

            stratum = str(rec["observed_flag_status"])
            k_by_stratum.setdefault(stratum, Counter())[lbl] += 1

            llm_lbl = str(llm_rows[iid]["llm_observed_wording_label"])
            if lbl == llm_lbl:
                k_vs_llm_agree += 1
            else:
                k_vs_llm_diffs.append(
                    {
                        "item_id": iid,
                        "video_id": vid,
                        "full_transcript_len": len(full_tr),
                        "truncated_at_600": len(full_tr) > 600,
                        "K_label": lbl,
                        "llm_draft_label": llm_lbl,
                        "K_note": note,
                    }
                )
            k_audit_rows.append(
                {
                    "item_id": iid,
                    "video_id": vid,
                    "review_assignment": rec["review_assignment"],
                    "full_transcript_chars": len(full_tr),
                    "K_observed_wording_label": lbl,
                    "K_error_or_domain_note": note,
                    "K_human_verified": True,
                }
            )
        else:
            rec["K_observed_wording_label"] = None
            rec["K_error_or_domain_note"] = ""
            rec["K_human_verified"] = False

        if rec["review_assignment"] in {"double_review_N_K", "N_only"}:
            clean_tags = [
                str(t)
                for t in (rec.get("hashtags") or [])
                if unicodedata.normalize("NFC", str(t)).strip().lstrip("#").lower()
                not in FORBIDDEN_DISCLOSURE_HASHTAGS
            ]
            n_blinded_rows.append(
                {
                    "item_id": iid,
                    "video_id": vid,
                    "author_handle": rec["author_handle"],
                    "food_category": rec["food_category"],
                    "has_transcript": rec["has_transcript"],
                    "caption": strip_forbidden_inline_hashtags(str(rec.get("caption") or "")),
                    "transcript_full": strip_forbidden_inline_hashtags(full_tr),
                    "hashtags": clean_tags,
                    "review_assignment": rec["review_assignment"],
                    "allowed_labels": [
                        "explicit_promo_cta",
                        "brand_or_venue_focus_no_cta",
                        "organic_or_general_review",
                        "unclear_or_noisy_text",
                    ],
                    "N_observed_wording_label": None,
                    "N_error_or_domain_note": "",
                    "N_human_verified": False,
                }
            )

        updated_wb_rows.append(rec)

    assert len(k_audit_rows) == 65
    assert len(n_blinded_rows) == 65

    # Atomically update review_sample_100.jsonl with K_* verified and transcript_full populated
    tmp_wb = wb_path.with_suffix(".jsonl.tmp")
    with tmp_wb.open("w", encoding="utf-8") as fp:
        for row in updated_wb_rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp_wb.replace(wb_path)

    k_audit_path = ev_dir / "khuong_65_full_transcript_audit.jsonl"
    with k_audit_path.open("w", encoding="utf-8") as fp:
        for row in k_audit_rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    n_sheet_path = ev_dir / "nguyen_65_blinded_fulltext_sheet.jsonl"
    with n_sheet_path.open("w", encoding="utf-8") as fp:
        for row in n_blinded_rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    pu_summary = compute_pu_observable_summary(df_videos)
    clf_all_std = evaluate_observed_ad_vs_ec_classifier(
        df_videos, test_fraction=0.30, seed=42, n_boot=500, min_df=3, exclude_platform_campaign_tags=False
    )
    clf_all_no_mcn = evaluate_observed_ad_vs_ec_classifier(
        df_videos, test_fraction=0.30, seed=42, n_boot=500, min_df=3, exclude_platform_campaign_tags=True
    )
    df_tr = df_videos[df_videos["has_transcript"].fillna(False)].copy()
    clf_tr_std = evaluate_observed_ad_vs_ec_classifier(
        df_tr, test_fraction=0.30, seed=42, n_boot=500, min_df=2, exclude_platform_campaign_tags=False
    )
    clf_tr_no_mcn = evaluate_observed_ad_vs_ec_classifier(
        df_tr, test_fraction=0.30, seed=42, n_boot=500, min_df=2, exclude_platform_campaign_tags=True
    )

    k_summary = {
        "auditor": "K",
        "k_verified_count": 65,
        "n_verified_count": 0,
        "k_items_with_post_600_transcript": sum(1 for x in k_audit_rows if x["full_transcript_chars"] > 600),
        "k_label_counts": dict(sorted(Counter(x["K_observed_wording_label"] for x in k_audit_rows).items())),
        "k_by_observed_flag_stratum": {
            st: dict(sorted(cnt.items())) for st, cnt in sorted(k_by_stratum.items())
        },
        "k_vs_llm_draft_agreement_65": round(k_vs_llm_agree / 65.0, 4),
        "k_vs_llm_disagreement_count": len(k_vs_llm_diffs),
        "k_vs_llm_disagreements": k_vs_llm_diffs,
    }
    (ev_dir / "khuong_65_audit_summary.json").write_text(
        json.dumps(k_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    v2_report = {
        "study_id": "m4_2_observed_disclosure_study_v2_k_review",
        "corpus_snapshot_id": manifest.snapshot_id,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "process_peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        },
        "target_policy": {
            "undisclosed_sponsorship_status": "DEFERRED",
            "unlabeled_items_treated_as_verified_negative": False,
            "flag_feature_leakage_excluded": True,
            "inline_caption_hashtag_bigram_leakage_blocked": True,
            "historical_audio_prosody_joined": False,
            "bootstrap_mode": "author_cluster_resample",
        },
        "review_workbook": {
            "path": "data/evaluation/m4_2_disclosure/review_sample_100.jsonl",
            "sha256": _sha256_file(wb_path),
            "total_items": 100,
            "double_review_overlap_count": 30,
            "N_assigned_count": 65,
            "K_assigned_count": 65,
            "K_human_verified_count": 65,
            "N_human_verified_count": 0,
            "human_review_completed": False,
        },
        "k_human_audit_summary": k_summary,
        "corpus_pu_observable_summary": pu_summary,
        "grouped_genuine_target_classifiers": {
            "all_observed_ad_only_vs_ec_only": clf_all_std,
            "all_observed_ad_only_vs_ec_only_ablate_platform_campaign_tags": clf_all_no_mcn,
            "transcribed_observed_ad_only_vs_ec_only": clf_tr_std,
            "transcribed_observed_ad_only_vs_ec_only_ablate_platform_campaign_tags": clf_tr_no_mcn,
        },
        "provenance": {
            "corpus_manifest_sha256": _sha256_file(corpus_dir / "manifest.json"),
            "prior_v1_study_sha256": _sha256_file(
                repo / "artifacts/benchmarks/m4_2_observed_disclosure_study.json"
            ),
            "code_files_sha256": {
                fname: _sha256_file(repo / fname)
                for fname in (
                    "packages/absa/disclosure.py",
                    "packages/absa/disclosure_eval.py",
                    "packages/absa/analyzer.py",
                    "packages/data_contracts/multimodal.py",
                    "apps/demo/presentation.py",
                    "apps/demo/ui.py",
                    "pipelines/audit_m4_2_disclosure/run_study.py",
                    "pipelines/audit_m4_2_disclosure/llm_draft_annotate.py",
                )
            },
        },
    }
    v2_study_out.write_text(json.dumps(v2_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"PASS: M4.2 K-audit & v2 study complete: "
        f"all_std PR-AUC={clf_all_std['metrics']['pr_auc']} (cluster CI {clf_all_std['metrics']['bootstrap_95_ci']['pr_auc']}), "
        f"all_no_mcn PR-AUC={clf_all_no_mcn['metrics']['pr_auc']}, "
        f"tr_std PR-AUC={clf_tr_std['metrics']['pr_auc']}, tr_no_mcn PR-AUC={clf_tr_no_mcn['metrics']['pr_auc']}, "
        f"K_vs_LLM_agree={k_summary['k_vs_llm_draft_agreement_65']}"
    )


if __name__ == "__main__":
    main()
