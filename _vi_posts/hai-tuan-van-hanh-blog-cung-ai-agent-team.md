---
layout: post
lang: vi
ref: hai-tuan-van-hanh-blog-cung-ai-agent-team
date: 2026-10-20
author: Ming Chen
title: "Hai tuần vận hành blog cá nhân cùng một đội AI agent"
tags: [ai-agent]
description: "Cách tôi vận hành blog Jekyll cùng đội AI coding agent trong hai tuần: làm việc theo issue, vòng review, và ship bài song ngữ."
redirect_from:
  - /2026/10/20/hai-tuan-van-hanh-blog-cung-ai-agent-team.html
---

Hai tuần vừa rồi, gần như mọi thay đổi trên blog này đều do các AI agent session được orchestrate làm ra, chứ không phải do mình ngồi gõ. Blog này là một Jekyll minima fork, deploy bằng GitHub Pages từ `master` — stack nhỏ, cũ, chẳng có gì bất ngờ. Và hóa ra đó lại là chỗ lý tưởng để kiểm chứng xem một đội agent thật sự làm được gì.

## Mọi việc bắt đầu từ issue

Thay đổi lớn nhất nằm ở cách làm việc: không có issue thì không làm gì cả. Mỗi issue ghi rõ bối cảnh, phạm vi, cái gì explicitly ngoài phạm vi, tiêu chí nghiệm thu, và đúng một risk label (`risk-low`, `risk-medium`, `risk-high` hoặc `risk-very-high`). Không label thì không có việc.

Nghe thì quan liêu, nhưng thực tế thì ngược lại — nhờ vậy mình mới dám quăng việc cho một agent session rồi đi chỗ khác. Issue chính là spec, worker session implement, PR khép vòng. Yêu cầu mơ hồ thì diff cũng mơ hồ; cái template bắt mình phải gọt yêu cầu cho sắc trước khi có một dòng code nào.

## Vòng review mới là sản phẩm thật

Mỗi PR đều qua các review session riêng, verdict ghi thẳng thành GitHub comment. Repo này chặn self-approval nên review không phải cho có — nó là cửa gác trước merge. Merge chỉ bằng squash, và chỉ khi CI xanh cộng với review xong.

Vòng này bắt được lỗi thật. Có ít nhất một lần feedback từ reviewer phải quay lại sửa code trước khi merge (phần test E2E cho comment có một commit fix chỉ tồn tại vì reviewer yêu cầu). Đó là toàn bộ ý nghĩa: agent viết nháp đầu rất nhanh, reviewer biến nó thành thứ ship được, và lịch sử git ghi rõ phần nào của ai.

## CI lo phần kiểm chứng nhàm chán

Suite E2E nằm dưới `tests/e2e/`, hiện tại có 42 file test. Nó chạy hai tốc độ: các static guard nhanh không cần browser (front matter, taxonomy, redirect, contract markup) cộng thêm ma trận browser bằng Playwright. Đợt gần đây bổ sung smoke test accessibility bằng axe-core, baseline visual-regression chụp screenshot, ma trận Firefox và WebKit bên cạnh Chromium, crawl toàn bộ link nội bộ kèm validate sitemap và feed, và test Giscus embed chạy trên bản build ở production-mode.

Ngoài ra còn có Lighthouse CI trên mọi PR vào `master`. Agent đẻ code rất nhanh; còn có được ship hay không là do các cửa gác quyết định.

## Hai tuần đó làm ra được gì

Mọi con số dưới đây đều được kiểm lại từ git history và danh sách PR đã merge tại thời điểm viết bài (20/10/2026) — cái gì không kiểm được thì không có mặt ở đây:

- **Tốc độ merge.** Các PR từ #160 tới #217 đều merge trong hai ngày 19–20/10: fix content, i18n, refactor và loạt test kể trên. Trước đó nữa là nền sidebar song ngữ, nhưng riêng hai ngày này đã là đợt ship dày nhất từ trước tới giờ của blog.
- **Ship song ngữ.** Site chạy đầy đủ Anh/Việt: nút chuyển ngôn ngữ dạng pill gọn, hreflang alternate trong sitemap và head trang, chrome bài viết được localize (tiêu đề Tags/Comments, footer, alt text). Lúc viết bài này có 7 bài tiếng Anh dưới `_posts/` so với 6 bài tiếng Việt dưới `_vi_posts/` — bản dịch đi sau bản gốc là chủ ý, và mỗi trang chủ ghi tổng số của riêng mình thay vì giả vờ hai bên bằng nhau.
- **UX audit và đoàn tàu fix.** Một đợt audit read-only trên site live chấm điều hướng 6.6, mobile/accessibility 6.5, đọc/performance 6.0 trên thang 10. Audit được chẻ thành mười ba issue mỗi issue một fix (#139–#151, mười hai `risk-low` và một `risk-medium`), mỗi issue đóng bằng một PR nhỏ: kích thước tap-target, accessible name cho link footer, giữ đúng một H1 ở trang portfolio, số đếm bài viết đúng ngữ pháp, chuyển ngôn ngữ giữ nguyên vị trí đọc, và còn nữa.
- **Refactor sạch code.** Các partial dùng chung thay chỗ copy-paste: một partial tag-label cho chip, trang tag và sidebar; một partial ref-resolution dùng chung cho alternate, switcher và notice; CSS chẻ thành các partial theo phạm vi; số bài mỗi trang pagination chỉ khai báo một nơi.
- **Chính quy trình viết bài này.** Bài bạn đang đọc cũng đi qua đúng pipeline đó: template article issue kèm label, intake scan tự nhặt article issue, role và skill cho người viết, flow chat-draft để bắt đầu từ note nháp, và CI hỗ trợ ảnh đính kèm ngoài.

## Agent vẫn còn sai ở đâu

Nói thật, và chỉ nói những gì mình quan sát được: agent rất vui vẻ đẻ ra diff trông như xong rồi nhưng thật ra chưa — danh sách lỗi của đợt audit (element tương tác lồng nhau, H1 bị trùng, URL trần, alt text cộc lốc) chính là bộ mặt của "trông như xong" khi thiếu kiểm chứng. Chúng nó còn hay lan man phạm vi: để tự nhiên, một session sẽ sửa ba thứ trong khi issue chỉ yêu cầu một, nên mới cần luật một-bài-một-PR và một-fix-một-PR. Và cả bộ máy đều vô dụng nếu tiêu chí nghiệm thu viết ẩu — đầu vào rác thì merge ra rác.

Mọi thứ kể trên đều bị bắt bởi cái gì đó mang tính cấu trúc (audit, vòng review, test), chứ không phải nhờ may mắn. Đó là bản trung thực của câu chuyện: agent thì nhanh, còn giàn giáo mới là thứ khiến chúng an toàn.

## Kết luận

Cách setup này hợp với việc nhỏ, yêu cầu rõ ràng, dễ revert, trên một stack có guardrail tốt — đúng như bản chất của một blog Jekyll cá nhân. Agent lo sản lượng; issue, review và CI lo phần phán đoán.

Những gì mình vẫn tự quyết bằng tay: mọi thứ `risk-high`, hướng đi sản phẩm của site, và việc một diff trông-có-vẻ-merge-được có thật sự tốt hay không. Sau hai tuần, việc của mình chuyển từ viết code sang viết issue và đọc diff. Với blog này, đó là một cuộc đổi chác khá hời.
