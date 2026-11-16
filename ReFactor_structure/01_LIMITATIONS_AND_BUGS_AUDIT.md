# 01. Báo cáo Rà soát Điểm yếu, Hạn chế & Lỗi Kỹ thuật

## 1. Hạn chế về Thiết kế & Chất lượng Dữ liệu (Data Layer)

1. **Phân mảnh dữ liệu (Data Silos):**
   - Dữ liệu sạch bị tách thành 6 file `.parquet` rời rạc không liên thông.
   - Nghiêm trọng nhất: `script_gendata.parquet` (2.652 video dùng để sinh kịch bản) trùng tới **2.639 ID** với `final_location_food_data.parquet`, nhưng **không được merge cột `foods`, `city_std`, `district_std` và cũng mất luôn `author.uniqueId`**. Hệ quả là công cụ tạo kịch bản hoàn toàn "mù" thông tin món ăn và địa điểm.
2. **Xóa nhầm dữ liệu quý do ngưỡng cắt cơ học (`> 66,67% null`):**
   - Trong `02_DEP_01-Preprocess_video_data.ipynb`, nhóm xóa mọi cột thiếu trên `66,67%`. Cụm cột check-in địa điểm chính chủ `poi.name`, `poi.address` có mặt ở **32,9% video (23.448 dòng, tức thiếu 67,1%)** đã bị xóa sạch, dẫn tới việc sau đó phải dùng LLM đoán lại địa điểm từ câu nói và gặp nhiễu (ví dụ *"Bún đậu Hà Nội ở Quận 7"* bị gán `city_std = "hà nội"` cho 20 video ở Quận 7).
   - Hơn **20.000 file transcript** trong `data/transcripts/` bị bỏ phí, không được đưa vào kho mẫu kịch bản.
   - Việc điền cứng `"others"` cho cột chuỗi và `median` cho cột số lên dữ liệu thiếu làm sai lệch ngữ nghĩa gốc.
3. **Bộ nhãn nội dung bị lệch nặng & thiếu các chiều thực tiễn:**
   - Trong `script_gendata.parquet`, nhãn do LLM gán bị bão hòa: `content_style` có **98,7%** (`2.619/2.652`) là `"Đời thường"` (`"Sang trọng"` chỉ có 5 bài); `tone_of_voice` có **95,0%** (`2.519/2.652`) là `"Thân thiện"`; `audience_target` có **81,0%** (`2.149/2.652`) là `"Người trẻ (Gen Z)"`. Khả năng lọc phân loại thực tế rất thấp.
   - **Thiếu hoàn toàn các chiều ngữ cảnh quan trọng khi sản xuất video:** Hoàn cảnh ăn uống (`occasion`: ăn đêm, hẹn hò, nhậu, cơm trưa văn phòng, ngày mưa...), Phân khúc giá (`price_tier`: sinh viên `<50k` vs nhà hàng/fine-dining), Cây phân loại món ăn chuẩn hóa, và Ngôn ngữ hình ảnh thực tế (`visual hook`, nhịp cắt cảnh).
4. **Dữ liệu đóng băng & thiếu Pipeline tự động:**
   - Dữ liệu dừng từ `19/03/2025` (đã cũ trên 1,5 năm so với xu hướng TikTok).
   - Quy trình xử lý nằm rời rạc trên các Notebook có gán cứng đường dẫn cá nhân (`os.chdir("/Users/vophuhan/...")`), chưa tự động hóa bằng Airflow/orchestrator.

---

## 2. Hạn chế về Kiến trúc AI & Retrieval (AI / RAG Layer)

1. **2/3 công cụ AI dùng Prompt Template tĩnh (0% Retrieval):**
   - `research.py` và `suggestion.py` (chia cứng 3 loại: Review, Mukbang, Nấu ăn) chỉ gọi Gemini với template `.md` cố định, hoàn toàn không truy xuất bất kỳ insight hay mẫu thực tế nào từ 70.996 video.
2. **Retrieval trong `write_scripts.py` chưa thực chất:**
   - Không có **Semantic/Vector Search** hay **Hybrid Search** theo món ăn, không gian quán, mức giá, hoàn cảnh.
   - Không lọc video mẫu theo **thời lượng tương ứng** (`video.duration`): người dùng yêu cầu kịch bản 15 giây vẫn lấy mẫu video dài 2–3 phút rồi ép cắt chữ theo tốc độ nói trung bình, làm hỏng cấu trúc nhịp điệu.
   - Xếp hạng mẫu theo `playCount` tuyệt đối khiến các kênh triệu follower chiếm hết top mẫu, bỏ qua các video có kịch bản đột phá vượt chuẩn kênh (`viral_multiplier`) của các kênh vừa và nhỏ.
3. **Bỏ phí cấu trúc kịch bản đã bóc tách & tự bịa cảnh quay:**
   - Các cột `hook_content`, `body_analysis`, `cta_content`, `highlight_sentences` có sẵn trong `script_gendata.parquet` nhưng không được đưa vào prompt; thay vào đó chỉ ném thô 20 đoạn `transcript` kèm câu mẫu sáo rỗng (*"Trời ơi ngon gì đâu luôn á", "ăn là ghiền"*).
   - Toàn bộ phần `visual_description` (cảnh quay), `setting`, `characters` ở bước định dạng JSON là do LLM tự bịa theo khung schema vì dự án không trích xuất dữ liệu khung hình từ video gốc.

---

## 3. Hạn chế về Phương pháp Phân tích & Thống kê (Analytics Layer)

1. **Thiên lệch chọn mẫu (Survivorship Bias) & lỗi tuần khuyết:**
   - Điều kiện thu thập bắt buộc kênh *"phải còn hoạt động trong năm 2025"* làm lượng video tự nhiên dồn về cuối giai đoạn; cộng thêm việc cắt top 20%/tuần với sàn tối thiểu `100` video ở 2 tuần đầu/cuối không đủ 7 ngày (`Y2023_W47` và `Y2025_W12`), khiến kết luận *"số lượng video ẩm thực tăng trưởng 23,4%"* thiếu cơ sở khách quan.
2. **Mâu thuẫn giữa nhận định trong `insights.md` và dữ liệu thực (`cleaned_video_info.parquet`):**
   - *Thứ 7 thấp nhất?* Thực tế Thứ 7 có **trung vị lượt thích cao nhất tuần** (`2.791,5`) và **trung vị lượt xem cao thứ 2** (`111.050`, sát nút Chủ Nhật `111.200`); Thứ 7 chỉ thấp ở tổng lượng view do ít bài đăng hơn ngày thường.
   - *Giờ vàng 11h–13h?* `11h` là đỉnh số lượng bài đăng, nhưng hiệu suất trung bình/trung vị của `12h` và `13h` thuộc nhóm thấp nhất ngày (trong khi `20h` và `23h–0h` cao hơn hẳn).
   - *Tối ưu 4–7 hashtag?* Đây chỉ là mức số đông hay dùng (TB `6,85`), còn nhóm đạt lượt xem trung bình và trung vị cao nhất thực tế là **2–3 hashtag** (`600k–764k` mean view, gấp đôi nhóm 6–7 hashtag).
3. **Thiếu nhất quán chỉ số & lỗi kiểm định trong báo cáo:**
   - Tồn tại **4 công thức khác nhau** cùng gọi là *"Tỷ lệ tương tác"* trên 4 trang (`(like+comment+share+collect)/view`, `heartCount/followerCount`, `heartCount/videoCount`, và trung bình cộng 4 tỷ lệ khác mẫu số trong `personal_analysis.py`).
   - Báo cáo Chương 8 (`trend_analysis.tex` dòng 76) ghi nhầm $p = 0.009$ cho kiểm định Chi-Square ($\chi^2 = 1164.65$, giá trị thực là $p = 1.26 \times 10^{-253}$).
   - Ở `engagement_insights.py`, tương quan giữa `stats.videoCount` và `avg_shares_per_video` của nhóm `Cao` là `+0.005` (không âm như kết luận cứng trên giao diện); biểu đồ vẽ trục log-log nhưng tính $\rho$ Pearson trên dữ liệu thô chưa log; đối chiếu tổng video trọn đời với tương tác trung bình của riêng 70 tuần.
   - Chưa có đánh giá độ chính xác (ground-truth benchmark) cho toàn bộ đầu ra do Gemini trích xuất.

---

## 4. Lỗi Kỹ thuật Phần mềm & Bảo mật (Engineering Layer)

### A. Danh sách các lỗi code cụ thể cần sửa
- `src/app/video_analysis/pages/single_hashtag.py` (dòng **310–311**): Kiểm tra `isinstance(x, list)` trên cột `hashtags` có kiểu `numpy.ndarray`, làm `target_videos` luôn trả về **0 dòng** khi tạo prompt AI cho hashtag đồng xuất hiện.
- `src/app/user_analysis/pages/correlation_analysis.py` (dòng **412, 493**) & `top_user_analysis.py` (dòng **278, 281**): Nội suy trực tiếp `{fig.to_image()}` vào f-string khiến Gemini nhận chuỗi ký tự `b'\x89PNG...'` thay vì đối tượng ảnh multimodal (`Part.from_bytes`), vừa tốn token vô ích vừa gây crash nếu thiếu `kaleido`/Chrome.
- `src/app/scriptwriting/pages/write_scripts.py` (dòng **127–153, 362**): Biến `duration` không được khởi tạo nếu `label_dict is None` gây `UnboundLocalError`; `max_output_tokens = int(word_count * 1.5)` quá thấp dễ cắt cụt tiếng Việt; dư dấu `"` khi render Markdown dòng 362.
- `src/app/user_analysis/pages/personal_analysis.py` (dòng **179–234**): Thang đo Gauge `views_per_follower` giới hạn `[0; 11,34%]` trong khi giá trị thực của 6 kênh là `25,12% – 200,53%` (tràn khung); 258/264 kênh không có dữ liệu kịch bản.
- `data/insights/insights.md` (dòng **34**): Lỗi khuyết chữ hiển thị lên UI (`"(khoảng phút)"`).
- `src/app/user_analysis/user_dashboard_app.py` (dòng **26–32**): Link HTML `?page=...` hỏng điều hướng và sai chính tả (`correlation_analysisanalysis`).
- `requirements.txt` & `src/crawler/`: Thiếu `scipy` và `pyarrow` trong `requirements.txt`; dùng `pyperclip` lỗi trên Linux server headless; `run_crawler.py` truyền tham số CLI nhưng `crawler.py` không nhận `sys.argv`.

### B. Danh sách 16 File lộ cứng API Key cần xóa & thu hồi (Revoke)
1. `src/app/scriptwriting/pages/write_scripts.py` — dòng **57**
2. `src/app/scriptwriting/pages/research.py` — dòng **217**
3. `src/app/scriptwriting/pages/suggestion.py` — dòng **66**
4. `src/app/video_analysis/pages/single_hashtag.py` — dòng **40**
5. `src/app/video_analysis/pages/video_performance.py` — dòng **37**
6. `src/app/video_analysis/pages/hashtags_insights.py` — dòng **38**
7. `src/app/user_analysis/pages/top_user_analysis.py` — dòng **291**
8. `src/app/user_analysis/pages/correlation_analysis.py` — dòng **431**, **503**
9. `src/app/user_analysis/pages/engagement_insights.py` — dòng **538**, **551**, **564**, **577**, **859**
10. `src/app/trend_analysis/pages/food_location_analysis.py` — dòng **740** *(trong comment)*
11. `notebooks/03_FE_01_01-Transcribe_audio_colab.ipynb` — dòng **357–389**
12. `notebooks/03_FE_01_02-Transcribe_error_audio_colab.ipynb` — dòng **105**
13. `notebooks/03_FE_01_03-Preprocess_transcript_data.ipynb` — dòng **79**
14. `notebooks/03_FE_02_01-Extract_food_location_colab.ipynb` — dòng **148–196**, **426**
15. `development/apis.py` — dòng **2–50** (37 Gemini API key)
16. `development/test_api.ipynb` — dòng **75**, **185**, **417** *(key bên thứ ba)*, **590**, **636**, **662**, **735**, **823–832**, **1250**, **1283**, **1746**

> **Lưu ý bảo mật:** Ngoài việc thay bằng `os.getenv("GEMINI_API_KEY")` / `st.secrets` trong code, bắt buộc phải **revoke (thu hồi)** toàn bộ các key cũ trên Google AI Studio vì chúng đã nằm trong lịch sử Git (`git log`).
