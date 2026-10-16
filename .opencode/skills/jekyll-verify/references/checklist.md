# Checklist hay vỡ khi đổi site

Soát bằng mắt sau khi build + test xanh, vì có lỗi chỉ lòi ra ở production.

## Comments (Giscus)

- `_config.yml` giữ nguyên `giscus.repo`, `repo_id`, `category_id` — đổi sai là
  thread bình luận không load (backend Giscus trả 403).
- Logic 3 nhánh trong `_includes/comments.html` phải còn nguyên: `giscus` khi đủ
  IDs, fallback Disqus cũ, render nothing khi provider `none`.
- Gate môi trường trong `_layouts/post.html` phải còn: chỉ render comments khi
  `JEKYLL_ENV=production` hoặc `site.comments.dev == true`.
- Bài có `comments: false` phải hiện `.comments-disabled-message`, không hiện
  thread.

## Cấu hình và nav

- `url` trong `_config.yml` phải khớp file `CNAME`, không hardcode domain khác.
- `minima.nav_pages` chỉ liệt kê file trang có thật (hiện tại: `about.md`,
  `portfolio.md`); sai tên là link nav 404.
- Đừng đổi `minima.date_format` nếu không có yêu cầu — format hiện tại là tiếng
  Việt (`Bài viết được đăng lúc: ...`).

## Bài viết và trang

- Tên file `_posts/` đúng `YYYY-MM-DD-slug.md`; Jekyll bỏ qua file ngày tương
  lai (future posts) nên bài "chưa xuất bản" thực ra là bài đặt ngày sai.
- `permalink` của trang tĩnh không trùng nhau, luôn bắt đầu bằng `/`.
- Ảnh/file đính kèm bỏ vào `assets/`, link tương đối để chạy được cả local
  lẫn production.

## Vệ sinh diff

- `git status --short` không được chứa `_site/`, `.jekyll-cache/`, `vendor/`,
  `Gemfile.lock` — đó là output của build/bundler, đã gitignore.
- Không commit file `AGENTS.md` vào `_site` (đã khai `exclude` trong config).
