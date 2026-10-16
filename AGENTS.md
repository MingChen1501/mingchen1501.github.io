# mingchen-site — hướng dẫn cho agent

Site cá nhân của Ming (https://mingchen.id.vn), fork từ theme Jekyll minima,
deploy bằng GitHub Pages từ nhánh `master`.

## Chạy và build

- Preview nội dung thật: `bundle exec jekyll serve` (dùng `_config.yml`).
- Build kiểm tra: `bundle exec jekyll build --trace`.
- `script/server`, `script/build`, `script/cibuild` phục vụ phát triển theme
  minima upstream (dùng `_config_theme-dev.yml` với nội dung mẫu) — không dùng
  để preview bài viết cá nhân.
- Thiếu gem thì chạy `bundle install` trước (cần mạng tới RubyGems).

## Kiểm thử

- E2E comments: `pip install -r tests/e2e/requirements.txt` rồi
  `python -m pytest tests/e2e -v` (chi tiết xem `tests/e2e/README.md`).
- `test_comments_markup.py` là static guard, chạy không cần browser.

## Quy ước nội dung

- Bài viết nằm trong `_posts/`, tên file `YYYY-MM-DD-slug-ascii.md`, nội dung
  tiếng Việt, slug chữ thường không dấu nối bằng `-`.
- Front matter tối thiểu: `layout: post`, `title`; bài của Ming thêm
  `author: Ming Chen`; muốn tắt bình luận cho bài đó thì `comments: false`.
- Trang tĩnh: `layout: page` + `permalink`; muốn lên thanh nav thì thêm đường
  dẫn vào `minima.nav_pages` trong `_config.yml`.
- Bình luận dùng Giscus (`comments.provider: giscus`); chỉ render ở production
  (`JEKYLL_ENV=production`), trừ khi `comments.dev: true`. Đừng phá logic trong
  `_layouts/post.html` và `_includes/comments.html` — test E2E phụ thuộc vào đó.
- `site.url` phải khớp `CNAME` (giữ canonical/SEO/feed đúng).

## An toàn

- Không sửa tay các đường dẫn do build sinh ra: `_site/`, `.jekyll-cache/`,
  `.sass-cache/`, `vendor/`, `.bundle/`, `Gemfile.lock` (plugin `jekyll-guard`
  sẽ chặn; muốn đổi dependency thì dùng `bundle install` / `bundle update`).
- Đổi `CNAME`, `url`, `giscus.repo_id` / `giscus.category_id` phải xác nhận với
  chủ site trước.
- `AGENTS.md` đã được `exclude` khỏi build nên không lọt ra site public.

## Trước khi xong việc

- Sửa `_layouts/`, `_includes/`, `_sass/`, `_config.yml`, `assets/` → build
  Jekyll + chạy `pytest tests/e2e -v`.
- Chỉ thêm bài viết mới → build smoke là đủ.
- Có skill riêng thì dùng: `jekyll-post`, `jekyll-verify`, `jekyll-review`.
