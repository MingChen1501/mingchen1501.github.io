# Review checklist cho site

## Liquid / layout (blocker nếu vỡ)

- `{% assign %}` / `{% include %}` còn đúng tên biến, đúng tên file partial.
- Nhánh provider trong `_includes/comments.html` và `_layouts/post.html` giữ
  nguyên thứ tự ưu tiên: `site.comments.provider` → Disqus cũ → `none`.
- `page.title` khi render ra HTML phải qua `escape` (hiện tại `_layouts/post.html`
  đã làm — đừng bỏ filter này).
- Không dùng biến config không tồn tại; Liquid render `nil` thành chuỗi rỗng và
  lỗi kiểu này rất khó thấy bằng mắt.

## Config `_config.yml` (blocker nếu sai production)

- `url`, `CNAME`, `giscus.repo_id`, `giscus.category_id`: sai một ký tự là mất
  canonical/feed hoặc mất thread bình luận.
- Key minima là `minima.nav_pages` (từ minima 3.0), không phải `site.header_pages`
  kiểu cũ.
- `exclude` phải giữ `AGENTS.md` để file hướng dẫn agent không lọt ra site public.

## Style / sass

- Chỉ đổi màu qua skin (`minima.skin`) hoặc 2 hook chính thức:
  `_sass/minima/custom-variables.scss` (biến), `_sass/minima/custom-styles.scss`
  (style). Không fork cả partial chỉ để sửa vài dòng.
- Tên biến cũ đã đổi ở minima 3.0 (`$brand-color` → `$link-base-color`...),
  dùng tên cũ là style im lặng không ăn.

## A11y và SEO

- Section comments giữ `aria-labelledby` + `<noscript>` fallback như hiện tại.
- Đừng bỏ `jekyll-seo-tag` / `jekyll-feed` khỏi `plugins` nếu không có lý do.
- Ảnh thêm `alt`, link ngoài không cần `target="_blank"` trừ khi thật sự cần.

## Nội dung bài viết

- Front matter đủ `layout: post` + `title`; ngày trong tên file hợp lệ.
- Đoạn mở đầu gọn (hiện ngoài homepage vì `show_excerpts: true`).
