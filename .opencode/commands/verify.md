---
description: Build Jekyll và chạy test E2E cho thay đổi hiện tại
---

Kiểm tra thay đổi hiện tại $ARGUMENTS theo skill `jekyll-verify`: xác định phạm vi
từ `git status`, chạy build và test tương ứng, báo cáo kết quả từng bước.
Dừng ở lỗi đầu tiên và đề xuất cách sửa, không mở PR khi còn đỏ.
