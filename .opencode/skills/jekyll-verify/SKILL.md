---
name: Jekyll Verify
description: Kiểm tra thay đổi trước khi mở PR (build Jekyll, test E2E comments). Dùng sau khi sửa layout, include, sass, config hoặc trước khi tạo PR.
---

# Verify trước PR

## Workflow

1. Xác định phạm vi từ `git status --short`:
   - Chỉ thêm/sửa bài trong `_posts/` → chỉ cần bước 2.
   - Động vào `_layouts/`, `_includes/`, `_sass/`, `_config.yml`, `assets/` → chạy đủ bước 2 + 3.
2. Build: `bundle exec jekyll build --trace` (thiếu gem thì `bundle install` trước).
3. Test: `python -m pytest tests/e2e -v` (lần đầu: `pip install -r tests/e2e/requirements.txt`).
4. Soát các điểm hay vỡ trong `references/checklist.md`.
5. Lỗi ở bước nào → sửa rồi chạy lại từ bước đó. Không mở PR khi còn đỏ.
