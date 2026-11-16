# Tài liệu Rà soát & Định hướng Tái cấu trúc Dự án (`21KHDL-TikTok-Analytics`)

Thư mục này lưu trữ toàn bộ kết quả phân tích hiện trạng, kiểm kê dữ liệu, danh sách lỗi/hạn chế, đặc tả kiến trúc và kế hoạch thực thi tái cấu trúc dự án theo chuẩn `SenticRAG`.

## Danh mục tài liệu

1. [**`00_OVERVIEW_AND_CURRENT_STATE.md`**](./00_OVERVIEW_AND_CURRENT_STATE.md) — Hiện trạng dự án cũ, mốc thời gian và kiểm kê 1,53 GB kho dữ liệu.
2. [**`01_LIMITATIONS_AND_BUGS_AUDIT.md`**](./01_LIMITATIONS_AND_BUGS_AUDIT.md) — Rà soát điểm yếu ở 4 tầng + danh sách 16 file lộ API Key.
3. [**`02_DATA_AND_RAG_REFACTOR_PROPOSAL.md`**](./02_DATA_AND_RAG_REFACTOR_PROPOSAL.md) — Phân tích thiết kế lại dữ liệu Gold & cơ chế Hybrid RAG.
4. [**`03_AI_ENGINEER_ARCHITECTURE_SPEC.md`**](./03_AI_ENGINEER_ARCHITECTURE_SPEC.md) — Bản đặc tả Kiến trúc chuẩn AI Engineer (FastAPI + Gradio `/demo/` + Docker Qdrant/Redis + Unified Gold Parquet).
5. [**`04_IMPLEMENTATION_PLAN.md`**](./04_IMPLEMENTATION_PLAN.md) — Kế hoạch triển khai chi tiết từng Task (`Task 1` → `Task 5`) với cam kết bảo toàn 100% dữ liệu gốc.
