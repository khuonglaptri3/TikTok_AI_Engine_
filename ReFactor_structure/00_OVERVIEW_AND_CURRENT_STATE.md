# 00. Hiện trạng Dự án & Kiểm kê Tài sản Dữ liệu

## 1. Tóm tắt dự án đã làm được gì?

Dự án thu thập và xử lý gần **71.000 video ẩm thực Việt Nam** của **264 TikToker** trong 70 tuần (`25/11/2023 – 19/03/2025`), kết hợp **Google Gemini API** để trích xuất lời thoại (transcript), tên món ăn, địa điểm và bộ nhãn cấu trúc nội dung từ các video nổi bật. Từ nguồn dữ liệu đó, nhóm xây dựng ứng dụng web đa trang trên **Streamlit** (`src/app/streamlit_app.py`) gồm hệ thống Dashboard phân tích hiệu suất kênh – video – xu hướng ẩm thực và bộ công cụ AI hỗ trợ nghiên cứu chủ đề, gợi ý góc quay cũng như viết kịch bản dựa trên video mẫu.

### Các mốc thời gian chính
- **Khởi tạo dự án:** `25/01/2025` (commit `5ef8b7c8`).
- **Mốc khóa dữ liệu:** `19/03/2025` (video mới nhất trong tập thu thập).
- **Hoàn thiện code & Bảo vệ đồ án:** `09/04/2025`.
- **Hoàn thiện Slide & Báo cáo LaTeX (98 trang):** `09/05 – 10/05/2025` (`slides/AoIDA-ADS-Final-Project.pdf`, `reports/Report.pdf`).
- **Commit dọn dẹp cuối cùng trên Git:** `03/07/2025` (commit `f142e565`).

---

## 2. Chi tiết các phân hệ đã xây dựng trên Webapp (`src/app/`)

### A. Hệ thống Dashboard Phân tích (3 cụm – 9 trang chuyên sâu)
1. **Cụm Phân tích Kênh / TikToker (`src/app/user_analysis/`):**
   - `correlation_analysis.py`: Thống kê tổng quan 264 kênh; Ma trận phân tán (Scatter Matrix) & Heatmap tương quan Pearson giữa `followerCount`, `heartCount`, `videoCount`; Histogram + Boxplot tùy chỉnh số bins và thang log; nhận xét AI.
   - `engagement_insights.py`: Phân 3 hạng kênh theo phân vị 33% và 66% follower (*Thấp ≤ 85.627*, *Trung bình 85.627–276.358*, *Cao > 276.358*); 4 biểu đồ Scatter (log-log + OLS) giữa tổng số video và tương tác/video; kiểm định **Kruskal-Wallis** so sánh tần suất đăng/tuần, số hashtag/video và thời lượng video giữa 3 nhóm.
   - `personal_analysis.py`: Tra cứu từng kênh theo khoảng ngày; Area chart lịch sử đăng bài; Calendar Heatmap lịch đăng theo tháng & thứ; Treemap Top 10 hashtag & thanh tỷ lệ Top 10 nhạc nền; riêng **6 kênh lớn** (`spicykim9386`, `haidangrevieww`, `khaikhampha`, `putaangi`, `trangtam2607`, `huynhanhtuan_dienvien`) có thêm 5 Gauge chart và bộ lọc phân tích nhãn kịch bản.
   - `top_user_analysis.py`: Xếp hạng Top $N$ (`1–50`) kênh theo lượt thích, số video, follower hoặc tỷ lệ tương tác (Bar chart + Pie chart + xuất CSV).

2. **Cụm Phân tích Video (`src/app/video_analysis/`):**
   - `video_performance.py`: Biểu đồ trục kép (số lượng video + trung bình/tổng/trung vị tương tác) theo 9 mốc thời lượng (`<10s` → `>10 phút`), 24 giờ trong ngày và 7 thứ trong tuần; Top 5 video cao nhất.
   - `hashtags_insights.py` & `single_hashtag.py`: Xếp hạng hashtag hiệu quả; đường cong mượt **LOWESS** tìm số lượng hashtag tối ưu; xu hướng hashtag theo Ngày/Tuần/Tháng; phân tích hashtag đồng xuất hiện (co-occurrence) và Top tác giả dùng một hashtag cụ thể.
   - `content_analysis.py`: Phân tích trên 3.004 video đã gán nhãn theo 5 thể loại ẩm thực; so sánh hiệu suất từng `hook_type`, `structure_style`, `tone_of_voice`, `pacing`, `cta_type`, `audience_target`, `content_style` bằng **Bar chart** và **Radar chart** (chuẩn hóa 0–100); phân phối mật độ từ ngữ (`word_per_second`).

3. **Cụm Phân tích Xu hướng Ẩm thực (`src/app/trend_analysis/pages/food_location_analysis.py`):**
   - Biến động lượng video qua 70 tuần kèm trung bình động 4 tuần, đường xu hướng tuyến tính, tự động gắn nhãn Đỉnh/Đáy ($\pm 1\sigma$) và đánh dấu mùa lễ (Giáng sinh, Tết Nguyên Đán, Trung thu); so sánh cùng kỳ các năm bằng Butterfly chart + **Welch's t-test**.
   - Phân bố địa lý: Top 10 tỉnh/thành; **Treemap Thành phố → Quận/Huyện** kèm chú thích các khu ẩm thực nổi tiếng tại Hà Nội & TP.HCM; kiểm định **Mann-Whitney U** (mức độ tập trung HN & TP.HCM) và **Chi-Square** (phân bố Bắc – Trung – Nam).
   - Tự động gom nhóm danh mục món ăn theo từ khóa chung và thuật toán 3 ngưỡng thích ứng phát hiện **món ăn mới nổi theo từng tuần** (loại trừ món xuất hiện ≥ 60% số tuần).

### B. Bộ công cụ AI hỗ trợ sáng tạo (`src/app/scriptwriting/`)
1. **Nghiên cứu chủ đề (`pages/research.py`):** Dùng System Prompt + User Prompt (cho phép sửa trực tiếp trên UI) gọi Gemini tổng hợp kiến thức thành 7 mục chuẩn (*Overview, Key Points, Examples, Challenges, Best Practices, Trends, Resources*) — **0% retrieval từ kho dữ liệu**.
2. **Gợi ý cách quay video (`pages/suggestion.py`):** Chia cứng 3 loại (*Review, Mukbang, Nấu ăn*), ghép mô tả người dùng vào 3 file template trong `data/prompts/suggestion/` để tư vấn góc máy, ánh sáng, âm thanh, phỏng vấn/dẫn chuyện, hiệu ứng và SEO — **0% retrieval từ kho dữ liệu**.
3. **Viết kịch bản tự động (`pages/write_scripts.py` & `tools/utils.py`):**
   - Bước 1: Dùng Function Calling (`label_schema.json`) trích nhãn phong cách & thời lượng từ mô tả người dùng (từ chối nếu không thuộc chủ đề ẩm thực).
   - Bước 2: Lọc mềm (soft relaxation) trên `script_gendata.parquet` (2.652 video), chấm điểm $\text{Score} = \text{playCount} / (\text{days\_since} + 1)^{0.7}$ để lấy **Top 20 video mẫu** + tốc độ nói trung vị (`~3,55 từ/giây`) + Top 10 hashtag.
   - Bước 3: Đưa 20 `transcript` mẫu vào `plain_script_prompt.md` sinh lời thoại thô theo số từ mục tiêu.
   - Bước 4: Gọi Gemini lần 2 chia lời thoại thành JSON phân cảnh (`video_description`, `duration`, `setting`, `characters`, `main_content`), tính lại `time_range` (`mm:ss-mm:ss`) bằng Python và cho phép sửa trực tiếp từng cảnh trên giao diện.
4. **Cẩm nang tối ưu kênh (`pages/insights.py`):** Hiển thị nội dung từ `data/insights/insights.md`.

---

## 3. Kiểm kê toàn bộ Kho Dữ liệu (~1,53 GB)

### A. 6 File "Gold" đang phục vụ trực tiếp cho App (nằm rải rác ở 4 thư mục)
| Đường dẫn file | Kích thước | Số dòng × cột | Nội dung chính |
| :--- | :---: | :---: | :--- |
| `data/processed/cleaned_user_info.parquet` | 93 KB | `264 × 30` | Hồ sơ 264 TikToker + thống kê kênh trọn đời + 8 chỉ số trung bình rút từ tập video. |
| `data/processed/cleaned_video_info.parquet` | 11 MB | `70.996 × 55` | Toàn bộ video đã làm sạch: metadata, `statsV2.*`, `author.*`, `music.*`, kỹ thuật video, `hashtags`, `year_week`. |
| `data/processed/content_features_6_users.parquet` | 2,4 MB | `1.335 × 33` | Video của 6 kênh lớn kèm `transcript`, nhãn kịch bản và `gemini_analysis`. |
| `src/app/trend_analysis/data/final_location_food_data.parquet` | 19 MB | `14.252 × 68` | Top 20% video mỗi tuần: 55 cột gốc + `transcript`, `takeaway_1..3`, `foods`, `city`, `district`, `city_std`, `district_std`. |
| `data/content_analysis/content_analysis_data.parquet` | 6,5 MB | `3.004 × 46` | Top 50 video/tuần: nhãn cấu trúc (`categories`, `hook_type`, `structure_style`, `tone_of_voice`, `pacing`, `cta_type`, `audience_target`, `content_style`), `hook_content`, `body_analysis`, `cta_content`, `word_per_second`. |
| `data/ScriptGen-data/script_gendata.parquet` | 6,2 MB | `2.652 × 45` | Lọc từ bảng 3.004 dòng trên (bỏ video ngoài ẩm thực, bỏ `transcript` rỗng, nội suy `duration=0`, giữ `word_per_second < 8`). |

### B. Kho dữ liệu Thô & Trung gian cực kỳ giá trị để tái khai thác
- `data/raw/` (**896 MB**): **203 thư mục** username chứa JSON gốc (`user_info.json`, `videos_info.json`).
- `data/interim/final_raw_videos.csv` (**73 MB** – `71.260 × 174 cột`): Bản gộp thô **vẫn còn giữ nguyên các trường quý đã bị xóa nhầm ở bước tiền xử lý**, bao gồm:
  - `poi.name` & `poi.address`: **23.448 video (32,9%)** có tên quán & địa chỉ check-in GPS chính chủ TikTok.
  - `poi.ttTypeNameTiny`: **22.330 video (31,3%)** có phân loại loại hình quán chuẩn của TikTok.
  - `poi.city`: **12.137 video (17,0%)**.
  - `playlistId`: **14.655 video (20,6%)** thuộc series nội dung của kênh.
  - `isECVideo`: **5.798 video (8,1%)** có gắn giỏ hàng TikTok Shop.
- `data/transcripts/` (**101 MB**): **23.122 file `.json`** lời thoại đã chạy Gemini (~22.516 bản hợp lệ — hiện mới dùng 2.652 bản cho công cụ viết kịch bản).
- `data/foods-and-locations/` (**57 MB**): **14.252 file `.json`** kết quả bóc tách món ăn & địa điểm.
