# M0.3 — Rendered `/demo/` Outputs on Real Recovered Data (`20261117_recovered_v1`)

## 1. Tab 1 — `offline_grounded` Script Studio Output

### Stage Timings
**Độ trễ từng chặng (Stage Timings):** `domain_gate_ms`: **0.22 ms** • `benchmark_ms`: **236.1 ms** • `retrieval_ms`: **799.49 ms** • `blueprint_synthesis_ms`: **0.28 ms** • `guardrail_ms`: **0.61 ms** • `total_ms`: **1036.83 ms**

### Thống Kê Mô Tả Ngách Trong Kho Lịch Sử
- **Lát cắt dữ liệu:** `video_format=Review quán ăn`, `food_category=Ăn vặt & Đường phố`, `city_norm=hồ chí minh`, `region=south`, `price_tier=budget_lt50k`, `occasion=an_dem`, `duration_bucket=short_20_45s`
- **Quy mô mẫu:** `2` video (`1` có lời thoại • `2` gắn GPS POI)
- **Lượt xem trung vị / P75:** `598,550` / `799,275` views (Tương tác trung vị: `2.44%`)
- **Phân bố thời lượng (IQR Q25 – Trung vị – Q75):** `29s` – **`29s`** – `29s`
- **Mật độ lời thoại ước tính:** `3.90` đơn vị cách trắng/giây • **Số lượng Hashtag IQR:** `9–10` thẻ (`#ancungtiktok`, `#foodreview`, `#bachtuotsotthai`, `#thaokiuugovap`, `#foodfestontiktok`, `#goitaiheo`)
- **Giờ đăng có lượt xem trung vị cao trong mẫu:** **19:00** (1,000,000 views), **17:00** (197,100 views)
- **POI do nền tảng ghi nhận:** Gò Vấp • TP. Hồ Chí Minh
_Thống kê lịch sử có thiên lệch chọn mẫu; không chứng minh tác động tăng viral hay xu hướng hiện tại._

### Bản Nháp Kịch Bản (`mode=offline_grounded`, model=`offline_evidence_blueprint_v1`)
_Nội dung sáng tạo từ nguồn tham khảo lịch sử; cần kiểm chứng nhận định và trải nghiệm trước khi sử dụng._
**Bối cảnh quay:** Không gian trải nghiệm thực tế tại Hồ Chí Minh, ưu tiên bàn gần nguồn sáng tự nhiên.  
**Giọng điệu (Persona):** Bản nháp sáng tạo; tách nguồn tham khảo và nhận xét cần trải nghiệm thực tế
#### 3 Phương Án Hook Mở Đầu (0–4s)
1. Nếu quay về ốc tại Hồ Chí Minh, bạn muốn kiểm tra hương vị hay mức giá trước?
2. Cùng lên ý tưởng tìm hiểu ốc: cần ghi lại điều gì để người xem tự đánh giá?
3. Mở đầu tham khảo từ kho @anngongovap: 'Về đây với, cùng tình yêu khát khao'
#### Bảng Phân Cảnh & Lời Thoại Tính Theo Tốc Độ Nói Thực Nghiệm
| Phân đoạn | Mốc thời gian | Góc máy & Hình ảnh | Lời thoại chi tiết | Số từ | Video tham chiếu |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **1. Hook mở đầu (0-5s giữ chân)** | `00:00-00:11` | 3 giây đầu: cận cảnh 45 độ món chính vừa bốc khói đặt xuống bàn trước khi quay mặt người | Nguồn cũ: "Về đây với, cùng tình yêu khát khao" Hôm nay mình lên ý tưởng tìm hiểu ốc tại Hồ Chí Minh. Khi quay thực tế, mình sẽ ghi lại món ăn và bảng giá trước khi đưa ra nhận xét. Bạn muốn | `44` | `7357939713132580103` |
| **2. Bối cảnh & Cận cảnh chế biến** | `00:11-00:22` | Góc POV gắp/cắt đôi món ăn để lộ nhân hoặc kết cấu bên trong và chấm ngập nước sốt | Nguồn cũ: "Về đây với, cùng tình yêu khát khao" Đây là thông tin trong nguồn cũ, cần kiểm tra lại khi đến quay. Mình sẽ ghi hình phần chế biến nếu được phép và mô tả đúng những gì quan sát được. | `43` | `7357939713132580103` |
| **3. Trải nghiệm hương vị & Giá trị thực** | `00:22-00:34` | Cảnh trung (medium shot) toàn bàn ăn kèm bảng giá hoặc không gian quán làm bằng chứng thực tế | Nguồn cũ: "Chị khẳng định, chị cam kết với tất cả khách hàng, nếu" Khi thử món, mình sẽ tách nhận xét về hương vị, khẩu phần và mức giá đang niêm yết. Những nhận định này cần trải nghiệm thực tế trước khi | `44` | `7416326498296057106` |
| **4. Tổng kết & Kêu gọi tương tác (CTA)** | `00:34-00:45` | Góc cận biểu cảm gật đầu xác nhận kèm text tóm tắt điểm cộng trên màn hình | Nguồn cũ: "Chấn động chấn động, quán ốc đồng giá 15 cành ngay tại" Sau khi quay và kiểm tra thông tin, mình sẽ tổng kết điểm phù hợp của ốc với nhu cầu người xem. Phần kết sẽ nêu rõ thời điểm trải | `44` | `7313084913899654401` |

**Caption gợi ý:** Bản nháp về ốc tại Hồ Chí Minh, lấy ý tưởng từ nguồn tham khảo lịch sử; cần kiểm chứng trước khi quay.  
**Hashtags:** `#ancungtiktok #foodreview #bachtuotsotthai #thaokiuugovap #foodfestontiktok #goitaiheo`
#### Hướng Dẫn Quay Dựng Thực Chiến
- **Góc quay:** 3 giây đầu: cận cảnh 45 độ món chính vừa bốc khói đặt xuống bàn trước khi quay mặt người
- **Góc quay:** Góc POV gắp/cắt đôi món ăn để lộ nhân hoặc kết cấu bên trong và chấm ngập nước sốt
- **Góc quay:** Cảnh trung (medium shot) toàn bàn ăn kèm bảng giá hoặc không gian quán làm bằng chứng thực tế
- **Ánh sáng & Âm thanh:** Dùng micro cài áo thu rõ giọng nói, giữ lại 15-20% âm thanh ASMR tự nhiên khi cắt/nhai giòn hoặc xèo xèo
- **Ánh sáng & Âm thanh:** Tránh đèn vàng gắt chiếu thẳng từ đỉnh đầu làm xỉn màu nước dùng và rau sống
- **Nhịp dựng:** Tốc độ thoại mục tiêu của ngách: ~3.9 từ/giây; cắt bỏ toàn bộ khoảng nghỉ thở thừa >0.3s
- **Nhịp dựng:** Phân bố thời lượng lịch sử của lát cắt: 29s - 29s (trung vị 29s); không chứng minh thời lượng tối ưu
#### Kiểm Định Guardrail: **ĐẠT KIỂM TRA CẤU TRÚC**
- Tổng số từ: `175` từ • Thời lượng ước tính: `44.9s` (Mục tiêu: `45.0s`, lệch `-0.1s`) • Tỷ lệ trích dẫn hợp lệ: `100%`
  - ⚠️ Kiểm tra cấu trúc, mã nguồn và thời lượng; chưa xác minh nội dung từng nhận định với nguồn.

### Bằng Chứng Video Viral Truy Xuất (`mode=hybrid_rrf`, `5` ứng viên)

#### #1 • [@anngongovap](https://www.tiktok.com/@anngongovap/video/7357939713132580103) (`7357939713132580103`) — **18,200 views** (`0.2x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Ăn vặt & Đường phố` | `budget_lt50k` | `26s` | 📍 TP. Hồ Chí Minh — quận 4 — hồ chí minh
- **Hook gốc:** _Về đây với, cùng tình yêu khát khao_
- **Ý chính / Nội dung:** Bài hát thể hiện niềm khát khao yêu đương và mong muốn hòa mình vào hạnh phúc.; Lời bài hát khuyến khích mọi người đừng từ bỏ giấc mơ và luôn tin vào tình yêu.

#### #2 • [@minn.cookie](https://www.tiktok.com/@minn.cookie/video/7416326498296057106) (`7416326498296057106`) — **467,500 views** (`2.0x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Ăn vặt & Đường phố` | `budget_lt50k` | `131s` | 📍 Ốc Tự Nhiên 2 - Trần Trọng Cung — quận 7 — hồ chí minh
- **Hook gốc:** _Chị khẳng định, chị cam kết với tất cả khách hàng, nếu như có một cái loại ốc nào đấy mà khách hàng cảm thấy nó không tươi ngon hoặc là không..._
- **Ý chính / Nội dung:** Quán Ốc Tự Nhiên có đa dạng các loại ốc và hải sản tươi ngon, được nhập mới mỗi ngày.; Giá cả ở quán rất phù hợp với học sinh, sinh viên và nhân viên văn phòng.

#### #3 • [@didausaigon](https://www.tiktok.com/@didausaigon/video/7313084913899654401) (`7313084913899654401`) — **59,700 views** (`0.5x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Ăn vặt & Đường phố` | `budget_lt50k` | `60s` | 📍 District 10 — hồ chí minh
- **Hook gốc:** _Chấn động chấn động, quán ốc đồng giá 15 cành ngay tại trung tâm Sài Gòn đã ai biết chưa?_
- **Ý chính / Nội dung:** Quán ốc tại trung tâm Sài Gòn với giá cả phải chăng, chỉ 15k/món.; Ốc tươi ngon, đa dạng sốt, đặc biệt là sốt trứng muối.

#### #4 • [@theotheoriviu](https://www.tiktok.com/@theotheoriviu/video/7376222810332581138) (`7376222810332581138`) — **194,300 views** (`6.5x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Ăn vặt & Đường phố` | `budget_lt50k` | `78s` | 📍 Thủ Đức — hồ chí minh
- **Hook gốc:** _Ê mấy má ơi, tiệm ốc này ở Thủ Đức định dưỡng lắm, bởi vì anh chủ ở đây cân một ngày cũng cả trăm món mà giá cực kỳ sinh viên..._
- **Ý chính / Nội dung:** Tiệm ốc có nhiều món đa dạng, giá cả phải chăng, phù hợp với sinh viên.; Hải sản tươi ngon được lấy từ Phan Thiết, đảm bảo chất lượng và độ uy tín.

#### #5 • [@anngongovap](https://www.tiktok.com/@anngongovap/video/7482756230310677776) (`7482756230310677776`) — **13,900 views** (`0.1x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Ăn vặt & Đường phố` | `budget_lt50k` | `31s` | 📍 Gò Vấp — hồ chí minh
- **Hook gốc:** _Chỉ là người xưa, quan tâm nhau làm gì nữa._
- **Ý chính / Nội dung:** Bài hát nói về sự đau khổ và thất vọng trong tình yêu.; Nhân vật chính dường như đã trải qua một mối quan hệ tan vỡ.


---

## 2. Tab 2 — Evidence Explorer (`bánh mì thịt nướng Sài Gòn`)

### Stage Timings
**Độ trễ từng chặng (Stage Timings):** `filter_ms`: **7.45 ms** • `bm25_ms`: **3.97 ms** • `fusion_ms`: **0.18 ms** • `rerank_ms`: **16.84 ms** • `total_ms`: **29.67 ms**

### Thống Kê Mô Tả Ngách Trong Kho Lịch Sử
- **Lát cắt dữ liệu:** `video_format=Review quán ăn`, `city_norm=hồ chí minh`
- **Quy mô mẫu:** `9,631` video (`3,187` có lời thoại • `9,323` gắn GPS POI)
- **Lượt xem trung vị / P75:** `77,600` / `210,300` views (Tương tác trung vị: `3.91%`)
- **Phân bố thời lượng (IQR Q25 – Trung vị – Q75):** `37s` – **`63s`** – `80s`
- **Mật độ lời thoại ước tính:** `5.06` đơn vị cách trắng/giây • **Số lượng Hashtag IQR:** `5–9` thẻ (`#ancungtiktok`, `#learnontiktok`, `#reviewanngon`, `#vtmgr`, `#food`, `#foodreview`)
- **Giờ đăng có lượt xem trung vị cao trong mẫu:** **14:00** (97,150 views), **17:00** (96,500 views), **15:00** (88,800 views), **16:00** (85,500 views)
- **POI do nền tảng ghi nhận:** Gò Vấp • District 1 • Bình Thạnh • District 10 • District 3
_Thống kê lịch sử có thiên lệch chọn mẫu; không chứng minh tác động tăng viral hay xu hướng hiện tại._

### Bằng Chứng Video Viral Truy Xuất (`mode=bm25`, `40` ứng viên)

#### #1 • [@didausaigon](https://www.tiktok.com/@didausaigon/video/7475992859783482642) (`7475992859783482642`) — **16,600 views** (`0.2x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Lẩu & Nướng` | `unspecified` | `59s` | 📍 District 1 — hồ chí minh
- **Hook gốc:** _Bánh mì là món ăn quốc dân từ Bắc vào Nam mà ai cũng mê._
- **Ý chính / Nội dung:** Tiệm bánh mì ngon và chất lượng tại Quận 1, có nhiều loại bánh mì đặc biệt.; Nguyên liệu tươi ngon, thịt nướng làm tại chỗ, đảm bảo vệ sinh và hương vị tự nhiên.

#### #2 • [@cohenvoithanhxuan](https://www.tiktok.com/@cohenvoithanhxuan/video/7369941510579588359) (`7369941510579588359`) — **2,100,000 views** (`39.3x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Món nước & Sợi` | `unspecified` | `105s` | 📍 Le Van Tam Park — hồ chí minh
- **Hook gốc:** _dành cho những ai chưa biết thì lễ hội bánh mì Việt Nam lần thứ ba đang diễn ra sôi động ngay tại công viên Lê Văn Tám Sài Gòn nè mọi..._
- **Ý chính / Nội dung:** Lễ hội bánh mì Việt Nam lần thứ ba diễn ra tại công viên Lê Văn Tám Sài Gòn, giới thiệu nhiều loại bánh mì và thương hiệu lâu đời.; Giá cả tại lễ hội được công khai, tạo điều kiện cho khách tham quan thoải mái lựa chọn.

#### #3 • [@didausaigon](https://www.tiktok.com/@didausaigon/video/7383229717656243476) (`7383229717656243476`) — **71,400 views** (`0.6x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Lẩu & Nướng` | `budget_lt50k` | `44s` | 📍 District 4 — hồ chí minh
- **Hook gốc:** _Tính ra là vào Sài Gòn tôi mới biết là có bánh mì bò lá lốt luôn đó mấy bà._
- **Ý chính / Nội dung:** Bánh mì bò lá lốt là một món ăn ngon và nổi tiếng ở Sài Gòn, đặc biệt là ở quận 4.; Gánh bánh mì này có tiếng và bán nhiều loại nhân, bao gồm bò lá lốt, thịt nướng, xíu mại, kèm theo sốt độc quyền.

#### #4 • [@buanaodian](https://www.tiktok.com/@buanaodian/video/7342846583089696008) (`7342846583089696008`) — **1,500,000 views** (`39.7x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Ẩm thực Chay & Healthy` | `casual_150_500k` | `76s` | 📍 Tân Phú — tân phú — hồ chí minh
- **Hook gốc:** _Buffet thịt nướng băng chuyền đầu tiên tại Sài Gòn mà chỉ với 199 xu một người thôi nè mấy bà ơi._
- **Ý chính / Nội dung:** Quán buffet thịt nướng băng chuyền đầu tiên tại Sài Gòn, giá vé 199 xu/người.; Thực đơn đa dạng với hơn 60 món nướng từ thịt heo, gà, bò đến hải sản, kèm rau, salad, kim chi và củ cải muối chua.

#### #5 • [@didausaigon](https://www.tiktok.com/@didausaigon/video/7405488027482524936) (`7405488027482524936`) — **145,900 views** (`1.3x` trung vị kênh)
- **Phân loại:** `Review quán ăn` | `Lẩu & Nướng` | `budget_lt50k` | `53s` | 📍 District 3 — hồ chí minh
- **Hook gốc:** _Cách để nhận biết một quán ăn ngon._
- **Ý chính / Nội dung:** Quán bánh mì ngon thường có các đặc điểm: bán trong hẻm, bán lâu năm (hơn chục năm), và bán gánh.; Bánh mì thịt nướng ở đây chỉ 20k, gồm thịt nướng, dưa leo và đồ chua, thịt trộn cả bò và heo.


---

## 3. Tab 3 — Comment Patterns & ABSA (Heuristic Baseline)

### Stage Timings
**Độ trễ từng chặng (Stage Timings):** `seeding_filter_ms`: **0.52 ms** • `absa_comparison_ms`: **0.43 ms** • `total_ms`: **0.99 ms**

### Chẩn Đoán ABSA Và Mẫu Bình Luận (Baseline Heuristic)
_Điểm chưa được hiệu chuẩn trên nhãn độc lập; không xác minh khách thật, bot, seeding hay tài trợ không công khai._
- **Chênh lệch điểm cảm xúc heuristic:** `+1.84` • **Chỉ số quảng bá heuristic:** `0.98` (không phải xác suất)
- **Bình luận hợp lệ:** `2` • **Bình luận nghi Seeding/Spam bị lọc:** `3`

| Khía cạnh (Aspect) | Điểm lời thoại | Điểm bình luận giữ lại | Chênh lệch |
| :--- | :---: | :---: | :--- |
| **Hương vị (Taste)** | `+0.89` | `-1.00` | +1.89; cần kiểm tra nguồn và độ phủ khía cạnh |
| **Giá cả (Price)** | `+0.89` | `-1.00` | +1.89; cần kiểm tra nguồn và độ phủ khía cạnh |
| **Vệ sinh & Không gian (Hygiene)** | `+0.79` | `-1.00` | +1.79; cần kiểm tra nguồn và độ phủ khía cạnh |
| **Phục vụ (Service)** | `+0.79` | `-1.00` | +1.79; cần kiểm tra nguồn và độ phủ khía cạnh |

#### Điểm Phàn Nàn Thực Tế Từ Người Xem (Pain Points)
- [taste] nước lẩu mặn chát mà bàn ghế bẩn đầy khói, nhân viên phục vụ quá chậm chờ 40 phút
- [price] nước lẩu mặn chát mà bàn ghế bẩn đầy khói, nhân viên phục vụ quá chậm chờ 40 phút
- [hygiene] nước lẩu mặn chát mà bàn ghế bẩn đầy khói, nhân viên phục vụ quá chậm chờ 40 phút
- [service] nước lẩu mặn chát mà bàn ghế bẩn đầy khói, nhân viên phục vụ quá chậm chờ 40 phút
- [taste] thịt ít xịu tính thêm rau bún vô đắt chứ không rẻ như quảng cáo lố
- [price] thịt ít xịu tính thêm rau bún vô đắt chứ không rẻ như quảng cáo lố

#### Danh Sách Bình Luận (Đã ẩn Seeding)
- ✅ `[CLEAN]` **@khach_that_1**: Nước lẩu mặn chát mà bàn ghế bẩn đầy khói, nhân viên phục vụ quá chậm chờ 40 phút
- ✅ `[CLEAN]` **@khach_that_2**: Thịt ít xịu tính thêm rau bún vô đắt chứ không rẻ như quảng cáo lố

---

## 4. Invalid Input Handling in `/demo/` UI

### 4.1 Out-of-domain brief (`422 UNSUPPORTED_DOMAIN`)
### ⚠️ Lỗi (`UNSUPPORTED_DOMAIN`)
Yêu cầu nằm ngoài lĩnh vực Ẩm thực & F&B TikTok Việt Nam. Vui lòng nhập chủ đề món ăn, quán ăn, đồ uống hoặc nấu ăn.

### 4.2 `gemini_free` without API key (`503 PROVIDER_KEY_MISSING`)
### ⚠️ Lỗi (`PROVIDER_KEY_MISSING`)
GEMINI_API_KEY is not set in .env. Configure a Free-Tier Gemini key or switch generation_mode to 'offline_grounded'.

### 4.3 `mode=dense` without Qdrant index (`503 INDEX_NOT_READY`)
### ⚠️ Lỗi truy xuất (`INDEX_NOT_READY`)
Dense Qdrant collection is offline or empty. Start docker-compose Qdrant or use mode='bm25' / 'hybrid_rrf'.

### 4.4 Blank brief in Tab 1 (`422` Pydantic validation)
### ⚠️ Lỗi (`422`)
{"detail": [{"type": "value_error", "loc": ["body", "brief"], "msg": "Value error, Value must be non-blank", "input": "     ", "ctx": {"error": {}}}]}

### 4.5 Blank query in Tab 2 (`422` Pydantic validation — empty message body bug `M0.3-UI-1`)
### ⚠️ Lỗi truy xuất (`422`)


### 4.6 Blank transcript in Tab 3 (`422` Pydantic validation)
### ⚠️ Lỗi (`422`)
{"detail": [{"type": "string_too_short", "loc": ["body", "transcript"], "msg": "String should have at least 5 characters", "input": "   ", "ctx": {"min_length": 5}}]}
