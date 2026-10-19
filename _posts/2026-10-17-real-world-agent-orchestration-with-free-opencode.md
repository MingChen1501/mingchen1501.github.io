---
layout: post
lang: en
ref: agent-orchestration-opencode-free
fallback_vi: true
author: Ming Chen
title: "Orchestration in Production: Blogging from the Beach with Free OpenCode"
tags: [ai-agent]
description: "Putting AI coding-agent orchestration to real use with free OpenCode: the orchestrator picks up the work, I just press merge — even from the beach."
---

>Đợt trước mình mới thử setup orchestration cho AI coding agent. Đợt này mình đem ra dùng thật, và có một chuyện mình không nghĩ tới: mình đang viết bài này từ bãi biển, chỉ bấm merge là xong.

## Lần này không còn là "thử"

- Đợt trước chỉ là setup rồi chạy vài tác vụ nhỏ cho biết. Đợt này mình đưa nó vào việc thật của chính site này: viết bài, sửa giao diện, dọn test.
- Thay vì ngồi gõ từng prompt cho từng session, giờ mình mô tả việc một lần, rồi để hệ thống tự chia việc và tự chạy.
- Và điều quan trọng nhất: mình không cần ngồi trước máy cả buổi nữa 😄

## Một orchestrator, vài worker

- Kiến trúc chính vẫn là orchestrator + worker. Orchestrator là session "đầu não": nắm danh sách việc, biết việc nào đang chạy, việc nào kẹt, việc nào xong.
- Worker là các session con, mỗi đứa ôm một việc: một issue, một lần sửa CI, một lần xử lý review comment.
- Mình giữ worker pool nhỏ thôi: 2 worker chạy song song, và để dành 1 slot cho việc gấp. Mở nhiều hơn thì mình cũng chẳng kịp đọc, mà tài nguyên free thì có hạn.

## Cron đánh thức định kỳ

- Phần mình thích nhất: orchestrator được đánh thức định kỳ bằng cron. Mỗi lần thức dậy, nó tự xem queue còn việc gì, session nào đang chạy, session nào đã chết giữa đường.
- Có việc mới thì nó tự spawn worker, tự giao task, tự theo dõi tới lúc có PR.
- Nghĩa là mình không phải "ngồi canh". Giao việc xong là mình đi làm việc khác, hoặc đi chơi, hệ thống tự chạy tiếp.

## Luồng issue -> PR -> reviewer -> merge

- Luồng chuẩn mình dùng: mỗi việc là một issue -> worker tạo branch, code, chạy verify, mở PR -> có reviewer đọc -> mình là người cuối cùng bấm merge.
- Chỗ mình giữ chặt nhất chính là bước cuối: merge vẫn phải là tay người. Orchestrator không được merge, agent cũng không. Đấy là ranh giới tin cậy của mình.
- Reviewer thì mình phải thay. Reviewer native của công cụ bị hỏng, nên mình dùng luôn một session worker làm reviewer: nó đọc diff ở đầu PR, tự viết comment vào từng chỗ cần sửa, rồi báo ngược lại cho session đang làm.
- Nói thật là reviewer bằng worker chưa "cứng" như mình kỳ vọng, nhưng nó vẫn bắt được mấy lỗi khiếm khuyết: thiếu meta description, tag không có page, sửa lan ra file ngoài phạm vi. Với mình thế là đủ để không tự bắn vào chân.

## Model free và chuyện bị đổi model giữa chừng

- Mình chạy bằng model free, nên hết quota hay bị rate limit là bình thường, không phải ngoại lệ.
- Hệ thống có cơ chế tự đổi sang model free khác khi model đang chạy bị limit. Session không chết, nó chỉ đổi "não" rồi chạy tiếp.
- Mình thấy ổn: các model trả lời không đồng nhất hoàn toàn, nhưng mỗi worker ôm một việc nhỏ, task rõ ràng nên không lệch nhiều.
- Đổi lại thì đừng mong nó nhanh như bản trả tiền. Chấp nhận chậm để không tốn tiền là cái deal của mình.

## Artifact và report là chỗ bàn giao

- Một chi tiết nhỏ nhưng cứu mình nhiều lần: worker không bàn giao bằng trí nhớ, mà bằng report và artifact.
- Report có trạng thái rõ ràng: checkpoint, cần quyết định, kẹt, xong — nhìn vào là biết việc đang tới đâu, khỏi phải hỏi lại.
- Mấy thứ không nằm trong PR — ghi chú, tài liệu nháp — được ghi ra thư mục artifact riêng, không nhét vào repo. Repo sạch, mình vẫn có cái để đọc.

## Cái được lớn nhất: bãi biển + cái điện thoại

- Đây mới là phần mình muốn kể. Vì luồng việc đã rõ và bước cuối chỉ là merge, mình có thể rời khỏi bàn làm việc.
- Ngồi ở bãi biển, mình mở điện thoại, xem orchestrator báo gì xong rồi, đọc PR, bấm merge. Việc trong queue vẫn được nhặt lên đều đều.
- Mình không code từ điện thoại — mình chỉ duyệt kết quả. Khác biệt lớn đấy: không cần gõ phím, chỉ cần quyết định.
- Cảm giác thật sự là "đi chơi mà việc vẫn chạy", chứ không phải "đi chơi mà trong đầu vẫn lo việc" 🏖️

## Nếu bạn định thử, mình nói trước vài điều

- Rate limit của bản free là có thật. Sẽ có lúc bạn phải chờ, phải đổi model, có lúc cả buổi chỉ nhích được một đoạn ngắn.
- Session hay đứng giữa đường. Nó không lỗi ầm ĩ, nó chỉ im. Bạn phải để ý và restart, chứ không phải cứ bấm chạy rồi đi ngủ là xong.
- Bạn vẫn là người merge, vẫn là người quyết định. Orchestration không thay bạn ra quyết định, nó chỉ bớt việc tay chân cho bạn.
- Điều quan trọng nhất: agent chạy bằng quyền người dùng của bạn. Nó đọc được file của bạn, chạy được lệnh của bạn, push được lên repo của bạn. Hãy nghĩ trước xem cho nó quyền gì, làm trong thư mục nào, và cái gì tuyệt đối không cho chạm vào.
- Nếu mới bắt đầu, mình khuyên làm nhỏ thôi: một repo, một loại việc, một reviewer. Đừng mở hết cùng lúc.

Tổng kết: đợt trước mình "thử", đợt này mình "áp dụng". Setup orchestration không biến AI thành kỹ sư tự động, nhưng nó làm được một thứ mình thích: mình rời khỏi bàn làm việc mà công việc vẫn nhích về phía trước — và mình vẫn là người bấm nút cuối.
