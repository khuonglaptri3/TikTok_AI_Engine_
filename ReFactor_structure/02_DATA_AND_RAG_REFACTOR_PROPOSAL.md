# 02. Định hướng Tái cấu trúc Dữ liệu & Hệ thống AI/RAG

Tài liệu này đề xuất lộ trình nâng cấp dự án từ kiến trúc *Dashboard tĩnh + Prompt Template rời rạc* sang kiến trúc **Unified Medallion Data + Hybrid Retrieval (Metadata + Vector RAG)** tận dụng tối đa nguồn dữ liệu sẵn có.

---

## 1. Tái quy hoạch Kiến trúc Dữ liệu (Data Restructure)

### A. Chuẩn hóa 3 tầng Medallion (`data/bronze`, `data/silver`, `data/gold`)
Xóa bỏ tình trạng 6 file Gold rời rạc ở nhiều thư mục. Toàn bộ tầng `data/gold/` được gom về **2 bảng chuẩn duy nhất** liên kết qua `author_id` và `video_id`:

1. **`data/gold/dim_creators.parquet` (264 dòng):**
   - Thông tin định danh & phân hạng kênh (`follower_tier`).
   - Các chỉ số nền của từng kênh tính theo **trung vị (median)** để chống nhiễu outlier: `median_plays`, `median_likes`, `median_engagement_rate`, `median_duration`, `avg_posts_per_week`.

2. **`data/gold/fact_videos_enriched.parquet` (70.996 dòng – trong đó ~22.500 dòng có full transcript & nhãn sâu):**
   - **Khôi phục các trường bị xóa nhầm từ `final_raw_videos.csv`:**
     - Cụm địa điểm chính chủ TikTok: `poi.name`, `poi.address`, `poi.city`, `poi.ttTypeNameTiny` (có sẵn cho **23.448 video**).
     - Cờ thương mại & chuỗi nội dung: `isECVideo` (**5.798 video**), `isAd`, `playlistId` (**14.655 video**).
   - **Nguyên tắc xử lý null mới:** Giữ nguyên `None`/`NaN` cho các trường không có dữ liệu; tuyệt đối không điền `"others"` hay `median` làm giả lệch dữ liệu.
   - **Hợp nhất toàn bộ dữ liệu AI đã chạy:** Nối toàn bộ **~22.516 bản transcript hợp lệ** từ `data/transcripts/*.json` + dữ liệu món ăn/địa điểm từ `final_location_food_data.parquet` vào chung bảng này.
   - **Ưu tiên địa điểm chính xác:** Nếu video có `poi.city` / `poi.address` chính chủ của TikTok thì ưu tiên dùng trước để sửa triệt để lỗi LLM đoán nhầm tên món thành tên tỉnh (như *"Bún đậu Hà Nội ở Quận 7"*).

---

## 2. Thiết kế lại Schema Nhãn Ngữ cảnh (Re-labeling trên ~22.500 video có thoại)

Loại bỏ các nhãn cũ bị lệch >90% (`"Đời thường"`, `"Thân thiện"`, `"Gen Z"`). Dùng LLM chạy batch trích xuất bộ nhãn mới có **tính phân loại thực tế cao** dựa trên `transcript + desc + poi.*`:

| Nhóm trường | Tên cột đề xuất | Giá trị / Ý nghĩa phục vụ truy xuất |
| :--- | :--- | :--- |
| **Định dạng chính** | `video_format` | `Review quán ăn`, `Review món lẻ/Đồ đóng gói`, `Hướng dẫn nấu ăn`, `Mukbang/ASMR`, `Food Tour/Top list`, `Vlog ăn uống trong ngày`. |
| **Món ăn chuẩn hóa** | `food_category`, `dish_entities` | Cây phân cấp chuẩn (*Món nước/Bún-Phở, Cơm/Bữa chính, Ăn vặt đường phố, Lẩu & Nướng, Đồ ngọt/Cafe/Trà sữa, Đồ chay/Healthy, Thực phẩm đóng gói*) + danh sách tên món cụ thể. |
| **Phân khúc giá** | `price_tier` | `Bình dân/Học sinh (<50k)`, `Tầm trung (50k–150k)`, `Nhà hàng/Buffet (150k–500k)`, `Cao cấp/Fine-dining (>500k)`, `Tự nấu tiết kiệm`, `Không đề cập`. |
| **Hoàn cảnh / Dịp** | `occasion` | `Ăn sáng/Cơm trưa nhanh`, `Ăn vặt xế chiều`, `Ăn đêm`, `Hẹn hò cặp đôi`, `Tụ tập bạn bè/Nhậu`, `Gia đình/Cuối tuần`, `Cơm nhà/Ở trọ sinh viên`, `Du lịch địa phương`. |
| **Tệp khán giả cụ thể** | `target_persona` | Chỉ gán khi có tín hiệu rõ: `Học sinh - Sinh viên`, `Dân văn phòng`, `Nội trợ/Gia đình`, `Người ăn kiêng/Gym/Chay`, `Tín đồ ăn cay/ăn vặt`, `Khách du lịch`, `Đại chúng`. |
| **Khung thời lượng** | `duration_bucket` | Chia cứng từ `video.duration`: `Ultra-short (<20s)`, `Short (20–45s)`, `Medium (45–90s)`, `Long (>90s)`. |
| **Giải phẫu kịch bản** | `hook_text`, `body_beats`, `cta_text` | Tách rõ **câu mở đầu 3–5s đầu (`hook_text`)**, **danh sách các ý triển khai thân bài (`body_beats`: không gian → gọi món → vị giác → giá cả → điểm trừ)**, và **câu chốt (`cta_text`)**. |

---

## 3. Đo lường lại "Video Thành Công" (`viral_score` chống thiên vị kênh lớn)

Thay vì chỉ xếp hạng theo `playCount` tuyệt đối, bổ sung vào bảng Gold 2 chỉ số chuẩn hóa:
1. **Tỷ lệ tương tác thống nhất toàn hệ thống (`engagement_rate`):**
   $$\text{engagement\_rate} = \frac{\text{diggCount} + \text{commentCount} + \text{shareCount} + \text{collectCount}}{\max(\text{playCount}, 1)}$$
2. **Hệ số bùng nổ vượt chuẩn kênh (`viral_multiplier`):**
   $$\text{viral\_multiplier} = \frac{\text{video\_playCount}}{\max(\text{creator\_median\_playCount}, 1000)}$$
   - Một kênh 30k sub nhưng có video đạt `viral_multiplier = 8.0x` chứng tỏ **kịch bản và cách mở đầu của video đó cực kỳ hiệu quả**, đáng được ưu tiên truy xuất làm mẫu hơn một video dưới mức trung bình (`0.4x`) của kênh 2 triệu sub.

---

## 4. Nâng cấp Bộ Công cụ AI sang Hybrid Retrieval (Metadata + Vector RAG)

1. **Xây dựng Vector Index (`data/gold/vector_index/`):**
   - Tạo trường văn bản tổng hợp `rag_document` cho mỗi video (ghép `video_format`, `food_category`, `dish_entities`, `poi.name`, `city_std`, `price_tier`, `occasion`, `hook_text`, `summarization`).
   - Nhúng bằng mô hình Multilingual/Vietnamese Embedding và lưu vào Vector DB nhẹ chạy local (`LanceDB` hoặc `Qdrant` / `Chroma`) kèm toàn bộ cột Metadata.

2. **Luồng sinh kịch bản mới (Thay thế Template cứng):**
   - **Bước 1 (Parse Intent):** Từ yêu cầu tự nhiên của người dùng (VD: *"Làm clip 40 giây review quán ốc đêm giá sinh viên ở Quận 4 đi ăn cùng đám bạn"*), trích xuất bộ filter: `duration_bucket = "Short (20–45s)"`, `occasion = "Ăn đêm" / "Tụ tập bạn bè"`, `price_tier = "<50k"`, `dish = "ốc"`.
   - **Bước 2 (Hybrid Search + Rerank):** Kết hợp lọc Metadata mềm với tìm kiếm tương đồng ngữ nghĩa trên `rag_document`, sau đó xếp hạng lại (rerank) theo công thức kết hợp độ khớp ngữ nghĩa + `viral_multiplier` + `engagement_rate` để lấy ra **5–10 video thành công sát hoàn cảnh nhất**.
   - **Bước 3 (Structure-Guided Generation):** Đưa trực tiếp bộ khung giải phẫu thật (`hook_text` → `body_beats` → `cta_text`), tốc độ nói trung vị của đúng nhóm `20–45s` đó và các từ khóa/hashtag thực tế vào LLM để sinh kịch bản mới — không dùng câu mồi rập khuôn.
   - **Bước 4 (Tích hợp luôn dữ liệu vào trang Nghiên cứu & Góc quay):** Khi người dùng nghiên cứu chủ đề hoặc xin gợi ý quay cho một món ăn, hệ thống truy xuất luôn thống kê thực tế từ bảng Gold (độ dài hiệu quả nhất, khung giờ tốt nhất theo trung vị, các kiểu Hook đang có `viral_multiplier` cao nhất của chính nhóm món đó) để tư vấn có số liệu dẫn chứng.

3. **Làm sạch Kỹ thuật & Vận hành:**
   - Thu hồi toàn bộ API key lộ, chuyển sang `.env` / `st.secrets`.
   - Sửa dứt điểm các bug trong `single_hashtag.py`, `correlation_analysis.py`, `top_user_analysis.py`, `write_scripts.py`, `personal_analysis.py` và bổ sung đầy đủ `scipy`, `pyarrow` vào `requirements.txt`.
   - Nếu đưa vào sử dụng thực tế năm 2026: viết lại pipeline thu thập dữ liệu định kỳ (cron/Airflow) và bổ sung bước trích xuất **3–5 khung hình đầu tiên (visual keyframes)** cho các video top để học cả ngôn ngữ hình ảnh thật.
