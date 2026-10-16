# Front matter cho bài viết

Mẫu tối thiểu (copy rồi đổi `title`):

```yaml
---
layout: post
title: "Tiêu đề bài viết"
author: Ming Chen
---
```

## Field hay dùng

| Field | Ý nghĩa |
|---|---|
| `layout: post` | Bắt buộc — dùng `_layouts/post.html` (có sẵn meta ngày, tác giả, comments). |
| `title` | Bắt buộc — hiển thị `<h1>` (layout đã `escape` nên cứ viết tự nhiên). |
| `author` | Tên tác giả. Bài của Ming ghi `author: Ming Chen`. |
| `date` | Mặc định lấy từ tên file `YYYY-MM-DD`. Chỉ ghi thêm khi cần giờ cụ thể, ví dụ `2026-10-17 08:00:00 +0700`. |
| `modified_date` | Ngày cập nhật — layout sẽ hiện thêm dòng "Updated:". |
| `categories` / `tags` | Phân loại, ví dụ `categories: [doi-song]`. Không bắt buộc. |
| `comments: false` | Tắt bình luận cho riêng bài này (mặc định bài nào cũng có Giscus). |

## Ví dụ thực tế trong repo

Xem `_posts/2026-10-14-setup-ai-coding-agent-orchestration.md`: front matter gọn
3 dòng + nội dung Markdown tiếng Việt với heading `##`.

## Lưu ý excerpt

Trang chủ bật `show_excerpts: true` nên Jekyll lấy đoạn văn đầu tiên làm tóm tắt.
Viết đoạn mở đầu ngắn gọn, đừng mở bài bằng blockquote dài hay code block.
