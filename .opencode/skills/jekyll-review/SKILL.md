---
name: Jekyll Review
description: Review thay đổi layout/include/sass/config của site Jekyll. Dùng khi cần soát diff trước PR hoặc đi kèm lệnh /review.
---

# Review thay đổi site

## Workflow

1. Lấy phạm vi: `git status --short`, `git diff --stat`, rồi `git diff`.
2. Soát từng file theo `references/review-checklist.md` — đúng trước, đẹp sau.
3. Báo cáo theo mức độ, mỗi mục kèm `file:line`:
   - **Blocker**: vỡ layout, mất comments, sai config production.
   - **Nên sửa**: maintainability, a11y, SEO/feed.
   - **Gợi ý**: style, chính tả, cải tiến nhỏ.
4. Không sửa code trong lúc review. Ghi nhận lại để sửa riêng.
