# Bộ 25 câu hỏi kiểm thử `/api/ask`

25 ca kiểm thử tiếng Việt cho /api/ask: truy xuất, bảng, tính toán, so sánh, suy luận và thiếu dữ liệu.

## Quy ước chấm

- `answered`: phải có ít nhất số citation quy định và các tín hiệu đáp án.
- `insufficient_context`: không được bịa số liệu và citations phải rỗng.
- Hai ca `calc_05`, `calc_06` chấp nhận cả trả lời đúng hoặc từ chối tính có kiểm soát.
- Các con số tiền tệ giữ nguyên đơn vị triệu/tỷ USD như báo cáo.

| # | ID | Nhóm | Câu hỏi | Đáp án/trạng thái kỳ vọng |
|---:|---|---|---|---|
| 1 | `direct_01` | truy_xuat_truc_tiep | Doanh thu Services của Apple trong năm tài chính 2024 là bao nhiêu? | 96,169 triệu USD (xấp xỉ 96.169 tỷ USD). Trạng thái: answered. |
| 2 | `direct_02` | truy_xuat_truc_tiep | Microsoft Cloud đạt doanh thu bao nhiêu trong FY2024 và tăng bao nhiêu phần trăm? | 137,4 tỷ USD, tăng 23% so với FY2023. Trạng thái: answered. |
| 3 | `direct_03` | truy_xuat_bang | Biên lợi nhuận gộp của NVIDIA trong FY2024 là bao nhiêu? | 72,7%. Trạng thái: answered. |
| 4 | `direct_04` | truy_xuat_bang | NVIDIA đã chi bao nhiêu cho capital expenditures trong FY2025 và FY2024? | FY2025: 3,4 tỷ USD; FY2024: 1,1 tỷ USD. Trạng thái: answered. |
| 5 | `direct_05` | truy_xuat_nghia_vu | Tại ngày 26/01/2025, remaining performance obligations trên các hợp đồng dài hơn một năm của NVIDIA là bao nhiêu và tỷ lệ dự kiến ghi nhận trong 12 tháng tới là bao nhiêu? | 1,7 tỷ USD; khoảng 39% dự kiến được ghi nhận trong 12 tháng tiếp theo. Trạng thái: answered. |
| 6 | `direct_06` | truy_xuat_nghia_vu | Remaining performance obligations của Microsoft tại 30/06/2025 là bao nhiêu, phần thương mại là bao nhiêu và khoảng bao nhiêu phần trăm dự kiến ghi nhận trong 12 tháng? | Tổng RPO 375 tỷ USD, trong đó 368 tỷ USD thuộc phần thương mại; khoảng 40% dự kiến ghi nhận trong 12 tháng. Trạng thái: answered. |
| 7 | `direct_07` | truy_xuat_theo_khu_vuc | Liệt kê doanh thu NVIDIA FY2024 theo khu vực Hoa Kỳ, Đài Loan, Trung Quốc (gồm Hồng Kông) và các quốc gia khác. | Hoa Kỳ 26,966 triệu USD; Đài Loan 13,405 triệu USD; Trung Quốc (gồm Hồng Kông) 10,306 triệu USD; các quốc gia khác 10,245 triệu USD. Trạng thái: answered. |
| 8 | `calc_01` | tinh_toan_duoc_ho_tro | Tính tốc độ tăng trưởng tổng doanh thu Apple từ FY2023 đến FY2024. | Khoảng 2,02% = (391,035 - 383,285) / 383,285 x 100, với đơn vị triệu USD. Trạng thái: answered. |
| 9 | `calc_02` | tinh_toan_duoc_ho_tro | Tính tốc độ tăng trưởng doanh thu Microsoft từ FY2023 đến FY2024. | Khoảng 15,67% = (245,122 - 211,915) / 211,915 x 100, với đơn vị triệu USD. Trạng thái: answered. |
| 10 | `calc_03` | tinh_toan_duoc_ho_tro | Tính tốc độ tăng trưởng doanh thu NVIDIA từ FY2024 đến FY2025. | Khoảng 114,20% = (130,497 - 60,922) / 60,922 x 100, với đơn vị triệu USD. Trạng thái: answered. |
| 11 | `calc_04` | tinh_toan_duoc_ho_tro | Tính tổng doanh thu của Apple và Microsoft trong FY2024. | 636,157 triệu USD = 391,035 + 245,122 triệu USD. Trạng thái: answered. |
| 12 | `calc_05` | tinh_toan_ngoai_luong_deterministic | Dựa trên doanh thu 57.006 triệu USD và lợi nhuận ròng 31.910 triệu USD, tính biên lợi nhuận ròng của NVIDIA trong ba tháng kết thúc ngày 26/10/2025. | Nếu hệ thống cho phép phép tính ngoài deterministic path: khoảng 55,98% = 31.910 / 57.006 × 100. Nếu tuân thủ giới hạn không tự tính, phải trả insufficient_context. Trạng thái: answered, insufficient_context. |
| 13 | `calc_06` | tinh_toan_ngoai_luong_deterministic | Ước tính phần RPO của NVIDIA tại 26/01/2025 dự kiến được ghi nhận trong 12 tháng tới. | Nếu được phép tính: khoảng 0,663 tỷ USD, tức 663 triệu USD. Nếu không, trả insufficient_context. Trạng thái: answered, insufficient_context. |
| 14 | `compare_01` | so_sanh_nam | So sánh doanh thu NVIDIA FY2025 với FY2024: chênh lệch tuyệt đối và tốc độ tăng trưởng là bao nhiêu? | FY2025 130,497 triệu USD so với FY2024 60,922 triệu USD; tăng 69,575 triệu USD, tương đương khoảng 114%. Trạng thái: answered. |
| 15 | `compare_02` | so_sanh_dong_san_pham | So sánh doanh thu Services của Apple giữa FY2023 và FY2024. | FY2024 là 96,169 triệu USD so với 85,200 triệu USD FY2023; tăng 10,969 triệu USD, khoảng 13% theo báo cáo. Trạng thái: answered. |
| 16 | `compare_03` | so_sanh_bang_can_doi | Tổng tài sản NVIDIA cuối FY2025 thay đổi thế nào so với cuối FY2024? | Tăng từ 65,728 triệu USD lên 111,601 triệu USD, tăng 45,873 triệu USD (khoảng 69,8%). Trạng thái: answered. |
| 17 | `compare_04` | so_sanh_cloud | Microsoft Cloud FY2025 tăng thế nào so với FY2024? | FY2025 168,9 tỷ USD so với FY2024 137,7 tỷ USD; tăng 23% theo báo cáo. Trạng thái: answered. |
| 18 | `reason_01` | suy_luan_nguyen_nhan | Yếu tố kinh doanh nào là động lực chính khiến doanh thu NVIDIA tăng mạnh trong FY2025? | Động lực chính là Data Center/Compute & Networking nhờ nhu cầu nền tảng điện toán tăng tốc và AI, đặc biệt các hệ thống GPU/data center. Trạng thái: answered. |
| 19 | `reason_02` | suy_luan_rui_ro | Tóm tắt các mắt xích có thể làm NVIDIA không đáp ứng được nhu cầu khách hàng trong chuỗi cung ứng. | Rủi ro gồm thiếu wafer/linh kiện/công suất; nhà cung cấp hủy cam kết hoặc tăng giá; foundry/contract manufacturer thiếu nguyên liệu, năng lực sản xuất, assembly/test/packaging; lead time và logistics kéo dài; phụ thuộc nhà cung cấp bên thứ ba và chuyển đổi công nghệ/quy trình. Trạng thái: answered. |
| 20 | `reason_03` | suy_luan_xu_huong | Tỷ trọng doanh thu NVIDIA ngoài Hoa Kỳ từ FY2023 đến FY2025 cho thấy xu hướng gì? | Tỷ trọng ngoài Hoa Kỳ giảm từ 69% FY2023 xuống 56% FY2024 và 53% FY2025, cho thấy cơ cấu doanh thu dịch chuyển tương đối về phía khách hàng có địa chỉ thanh toán tại Hoa Kỳ; không nên đồng nhất billing location với nơi sử dụng cuối. Trạng thái: answered. |
| 21 | `reason_04` | suy_luan_kenh_ban | Cơ cấu kênh phân phối Apple năm 2025 nghiêng về trực tiếp hay gián tiếp? | Nghiêng về kênh gián tiếp: 60% net sales qua kênh gián tiếp và 40% qua kênh trực tiếp, chênh 20 điểm phần trăm. Trạng thái: answered. |
| 22 | `reason_05` | suy_luan_backlog | RPO 375 tỷ USD của Microsoft tại 30/06/2025 nói gì về thời điểm ghi nhận doanh thu tương lai? | Đây là doanh thu đã phân bổ cho nghĩa vụ còn lại, gồm unearned revenue và khoản sẽ lập hóa đơn/ghi nhận trong tương lai. Microsoft dự kiến khoảng 40% được ghi nhận trong 12 tháng tới và phần còn lại sau đó; đây không phải toàn bộ doanh thu chắc chắn của một kỳ đơn lẻ. Trạng thái: answered. |
| 23 | `negative_01` | thieu_du_lieu | Doanh thu VinFast trong FY2024 là bao nhiêu? | Không đủ ngữ cảnh vì corpus không có filing VinFast. Trạng thái: insufficient_context. |
| 24 | `negative_02` | ngoai_pham_vi_thoi_gian | Tổng doanh thu Apple trong FY2019 là bao nhiêu? | Không đủ ngữ cảnh; corpus Apple hiện có bắt đầu từ FY2023 và không được lấy con số FY2019 từ kiến thức ngoài. Trạng thái: insufficient_context. |
| 25 | `negative_03` | ngoai_corpus | So sánh doanh thu smartphone của Samsung và Apple trong FY2024. | Không đủ ngữ cảnh vì corpus không có filing Samsung và không nên suy diễn số liệu đối thủ. Trạng thái: insufficient_context. |
