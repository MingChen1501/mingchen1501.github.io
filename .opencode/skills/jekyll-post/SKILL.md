---
name: Jekyll Post
description: Tạo bài viết mới cho site (tên file theo ngày, front matter chuẩn, build thử). Dùng khi viết thêm bài blog.
---

# Viết bài mới

## Workflow

1. Lấy tiêu đề bài + ngày đăng (mặc định hôm nay).
2. Tạo slug ascii: chữ thường, không dấu, từ nối bằng `-`. Tên file:
   `_posts/YYYY-MM-DD-<slug>.md`.
3. Đọc `references/front-matter.md` rồi viết front matter + nội dung tiếng Việt.
4. Chạy `bundle exec jekyll build --trace` để chắc chắn bài render được.
5. Mở file bài tương ứng trong `_site/` kiểm tra tiêu đề/ngày. Lưu ý trang chủ
   có `show_excerpts: true` nên đoạn mở đầu sẽ hiện ngoài homepage — viết đoạn
   đầu cho gọn.

Không commit thư mục `_site/` (đã có trong `.gitignore`).
