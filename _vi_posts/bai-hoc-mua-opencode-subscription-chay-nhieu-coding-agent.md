---
layout: post
lang: vi
ref: lessons-opencode-subscription-multiple-coding-agents
date: 2026-10-20
author: Ming Chen
title: "Bài học khi mua subscription OpenCode và chạy nhiều coding agent cùng lúc"
tags: [ai-agent]
description: "Bài học sau khi trả phí OpenCode và chạy nhiều coding agent cùng lúc: xoay vòng model, fallback review thủ công và kỷ luật chi phí."
redirect_from:
  - /2026/10/20/bai-hoc-mua-opencode-subscription-chay-nhieu-coding-agent.html
---

Chạy nhiều coding agent cùng lúc trên blog này dạy mình nhiều về vận hành hơn là về AI. Gần đây mình quyết định trả phí subscription OpenCode, và quyết định đó buộc mình phải nghĩ nghiêm túc về quota, lựa chọn model và kỷ luật quy trình. Dưới đây là những gì mình học được — viết thật, không quảng cáo.

## Vì sao phải trả phí: một quota dùng chung

Mọi AO session trong project này dùng chung một tài khoản OpenCode, nên orchestrator và worker rút từ cùng một quota. Một worker turn dài có thể làm orchestrator "đói" quota: orchestrator cần quota để kiểm tra trạng thái, spawn session và theo dõi PR, mà worker chạy cùng model sẽ rút đúng phần đó.

Setup của mình: gói **OpenCode Go, 10 USD mỗi tháng**, chỉ dùng model rẻ — chủ yếu là **DeepSeek (`deepseek-v4.1-flash`)** và **Muse (`muse-spark-1.3-contributor`)** — không dùng model premium/đắt tiền. [OWNER FACT NEEDED: ngày mua và con số quota/allowance của gói.]

Trả phí không xóa giới hạn; nó chỉ dời điểm nghẽn. Bài học thực sự là gói trả phí mà thiếu kỷ luật thì cũng cạn như free tier — chỉ là cạn muộn hơn.

## Workflow mà subscription phục vụ

Subscription tồn tại để phục vụ một workflow chặt chẽ, đã đối chiếu với rule orchestration của repo:

- **Tối đa một task worker tại một thời điểm**, cộng một buffer worker chỉ để tạo issue. Một worker = một task nhỏ = một PR.
- **Mỗi role là một session riêng**: issue-writer, dev, reviewer, fixer. Session không bao giờ review PR của chính mình.
- Merge chỉ bằng squash merge, khi CI xanh — và người bấm nút cuối cùng vẫn là mình.

Giới hạn một worker ban đầu là vì peak CPU trên máy mình, nhưng nó đồng thời là kỷ luật chi phí: càng ít turn dài chạy song song thì mỗi giờ càng ít quota bị đốt. [OWNER FACT NEEDED: đã thử remote host chưa, host nào, chi phí, kết luận ra sao — chạy agent ở nơi khác ngoài máy cá nhân vẫn là một lựa chọn.]

## Xoay vòng model: cách làm thực sự hiệu quả

Mọi worker/reviewer session đều chạy trên model **khác với model của orchestrator** (override bằng `ao spawn --model`). Rule tách model này tồn tại vì worker chạy cùng model với orchestrator sẽ rút cạn quota mà điều phối cần. Luôn giữ ít nhất hai free model khả dụng để lúc nào cũng có chỗ xoay vòng.

Dấu hiệu rate limit là các lỗi có cấu trúc dạng `provider.quota` / 429 / `FreeUsageLimitError` — hoặc worker im lặng bất thường trong khi còn việc chưa commit và chưa có PR. Khi đó, recipe xoay vòng đã kiểm chứng là:

1. Kill session bị kẹt (worktree của nó vẫn nằm trên disk cùng file chưa commit — không mất gì).
2. Spawn worker mới trên một free model **khác** cho cùng task, mang file sang.
3. Commit và mở PR từ session mới. Không bao giờ spawn lại trên model vừa lỗi.

Một đính chính đáng nói: không có lệnh nào đổi được model của session đang chạy, và xoay vòng là việc của orchestrator — prompt của worker không được hứa hẹn "tự đổi model khi bị rate limit". Một bài trước mình từng viết rằng hệ thống tự đổi model; thực tế đã kiểm chứng là kill rồi spawn lại, làm rõ ràng từng bước.

## Khi native reviewer lỗi: fallback review thủ công

Native AO reviewer đang hỏng/bị tắt ở project này, nên review được làm trong **AO worker session riêng, sau khi PR đã lên — không bao giờ trước đó**. [OWNER FACT NEEDED: các mốc thời gian quan sát thấy native reviewer lỗi, nếu muốn công bố.]

Kết luận review được đăng dưới dạng GitHub **comment**, vì GitHub chặn self-approval từ cùng tài khoản: AO approval không bao giờ được tính là GitHub approval và không cho phép merge. Worker-as-reviewer không hoàn hảo, nhưng vẫn bắt được lỗi thật — thiếu meta description, tag không có trang, sửa lố phạm vi — đủ để mình không tự bắn vào chân.

## Cái gì đốt quota, cái gì tiết kiệm quota

Những thứ đốt quota nhanh nhất:

- Worker turn dài cho task lớn, mô tả mơ hồ.
- Worker chạy cùng model với orchestrator.
- Nhiều session song song cùng rút từ một tài khoản.

Những thứ tiết kiệm được:

- Task nhỏ gọn, một task một PR, phạm vi chặt.
- Chỉ dùng model rẻ — DeepSeek `deepseek-v4.1-flash` và Muse `muse-spark-1.3-contributor`.
- Các guard check tĩnh trả kết quả trong vài giây thay vì vòng lặp agent dài.

[OWNER FACT NEEDED: con số quota thực tế và chi phí ngoài 10 USD/tháng của gói, nếu muốn công bố.] Mình không đưa ra nhận định nào về chất lượng, giá trị hay benchmark của model — chỉ nói workflow của mình đã tiêu tốn và tiết kiệm ở đâu.

## Kết luận: khi nào đáng trả phí

Trả phí đáng khi bạn chạy agent đủ thường xuyên để điểm nghẽn là coordination starvation — chứ không phải quyền truy cập model: một tài khoản dùng chung, một orchestrator phải luôn phản hồi, và worker làm việc thật mỗi ngày. Free tier là đủ khi bạn chỉ chạy task nhỏ thỉnh thoảng và chịu được việc chờ rate limit hay xoay model thủ công.

[OWNER FACT NEEDED: quan điểm hiện tại của mình — giữ gói trả phí hay quay lại free.]
