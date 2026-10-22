---
layout: post
lang: vi
ref: back-to-linux-fundamentals
date: 2026-10-22
author: Ming Chen
title: "Quay lại Linux căn bản sau nhiều năm vibe code"
tags: [linux-tooling]
description: "Ôn lại Linux căn bản sau nhiều năm làm thực tế: 20 ghi chú ngắn về filesystem, quyền, tiến trình và các công cụ shell quen thuộc."
redirect_from:
  - /2026/10/22/quay-lai-linux-can-ban.html
---

Hầu hết kiến thức Linux của mình đều đến từ việc làm, chứ không phải từ việc học bài bản. Nhiều năm qua mình toàn chắp vá mọi thứ bằng cách search, copy câu lệnh, gần đây thì nhờ AI hỗ trợ, và như vậy thường cũng đủ để xong việc trước mắt. Công việc hằng ngày cũng không bắt mình phải quay lại với nền tảng: server nhìn chung vẫn chạy, container che đi phần còn lại, và chỗ nào chưa hiểu thì cũng có cách vòng qua mà không cần hiểu thật sự.

Lần ôn lại một bộ flashcard gần đây cho thấy mình đã quên nền tảng nhiều thế nào. Chủ đề nào cũng thấy quen, nhưng không phải lúc nào cũng giải thích gọn được mà không đoán mò, nhất là quanh quyền file, signal và cấu trúc filesystem. Nên đây là ghi chú ôn tập của mình: cùng hai mươi câu hỏi đó, trả lời ngắn gọn bằng lời của mình như một điểm kiểm tra cá nhân, không phải tutorial và cũng không phải app học tập.

## Cấu trúc filesystem

**Các thư mục chính nằm ở đâu?** `/bin` chứa các câu lệnh người dùng thiết yếu, `/etc` chứa cấu hình hệ thống, `/home` chứa thư mục home của người dùng, `/var` chứa dữ liệu thay đổi như log và mail, `/tmp` chứa file tạm, `/usr` chứa chương trình và thư viện phụ, còn `/opt` chứa phần mềm add-on. Trên hầu hết distro hiện nay `/bin` là symlink tới `/usr/bin` sau usrmerge, nên sự phân chia này quan trọng ở chuẩn hơn là khi dùng hằng ngày.

## Quyền và sở hữu

**`rwx` nghĩa là gì, còn `rwxr-xr--` đổi ra số là bao nhiêu?** `r`, `w` và `x` lần lượt là đọc (4), ghi (2) và thực thi (1), lặp lại theo ba nhóm owner, group và others. `rwxr-xr--` nghĩa là owner làm được mọi thứ, group được đọc và thực thi, others chỉ được đọc, tức là 754.

**Đọc câu lệnh `chmod` thế nào?** Dạng số đặt cả ba nhóm một lúc, như `chmod 754 file`, còn dạng ký hiệu chỉnh từng nhóm với `u`, `g`, `o` hoặc `a` kết hợp `+`, `-` hoặc `=`. `chmod g+w,o-r file` thêm quyền ghi cho group và bỏ quyền đọc của others, giữ nguyên mọi thứ còn lại.

**`chown` đổi cái gì?** `chown user file` đổi owner, `chown :group file` chỉ đổi group, còn `chown user:group file` đổi cả hai cùng lúc. Đổi sở hữu thường cần quyền root hoặc `sudo`, nên ngoài thực tế hay đi kèm một lệnh `chmod` để sửa quyền cho đúng.

## Tiến trình và service

**Tiến trình là gì?** Tiến trình là một chương trình đang chạy, có vùng nhớ và PID riêng, được tạo ra như tiến trình con của một tiến trình khác trừ tiến trình đầu tiên. PID 1 là hệ thống init, trên hầu hết distro phổ biến hiện nay chính là `systemd`.

**Liệt kê tiến trình bằng `ps` thế nào?** `ps aux` dùng kiểu tùy chọn BSD để hiện mọi tiến trình kèm cột user, CPU và memory, còn `ps -ef` hiện ý tương tự theo kiểu POSIX với đầy đủ command line. `ps -u user` lọc theo chủ sở hữu, và pipe bất kỳ lệnh nào trong số đó qua `grep` để thu hẹp về một chương trình.

**`top` dùng để làm gì?** `top` hiện danh sách tiến trình đang chạy theo thời gian thực, kèm mức dùng CPU, memory và load average, làm mới sau mỗi vài giây. Trong đó `q` để thoát, `k` để nhập PID cần kill, còn `M` để sắp xếp theo memory.

**Những signal nào cần nhớ thật?** SIGTERM (15) yêu cầu tiến trình tự kết thúc gọn gàng, SIGKILL (9) bắt dừng ngay không dọn dẹp và không thể bắt hay chặn, SIGHUP (1) ngày xưa nghĩa là ngắt kết nối và nay hay dùng để bảo daemon reload, còn SIGINT (2) là signal khi bấm `Ctrl+C`. Thói quen an toàn là `kill PID` hoặc `kill -15` trước, chỉ dùng `kill -9` khi tiến trình không chịu thoát.

**Quản lý service bằng `systemctl` thế nào?** `start`, `stop`, `restart` và `status` điều khiển hoặc kiểm tra service ngay lúc đó, còn `enable` và `disable` quyết định service có chạy khi boot hay không. Sau đó `journalctl -u name.service` cho xem log của service đó, thường là bước tiếp theo khi restart thất bại.

## Shell, pipe và tìm kiếm text

**Tìm kiếm text bằng `grep` thế nào?** `grep -r` tìm đệ quy qua các thư mục, `-i` bỏ qua hoa thường, `-n` in số dòng, còn `-v` đảo ngược kết quả để hiện những dòng không khớp pattern. Bản thân pattern là biểu thức chính quy, nên đặt trong dấu nháy để shell không expand ký tự trước.

**Pipe và redirect liên quan với nhau ra sao?** `|` đưa output của lệnh này thành input của lệnh kia, `>` ghi output ra file theo kiểu ghi đè, `>>` ghi nối thêm, còn `<` đưa file vào làm input. `2>` redirect lỗi, `&>` redirect cả output lẫn lỗi trong Bash, còn `2>&1` trộn lỗi vào luồng output chuẩn để cả hai đi chung qua một pipe hay một file.

**Tìm file bằng `find` thế nào?** `-name` khớp theo tên file, `-type f` chỉ lấy file thường, `-mtime -7` chỉ lấy file sửa trong bảy ngày gần nhất, còn `-size +100M` chỉ lấy file lớn hơn 100 MB. `-delete` xóa trực tiếp các kết quả khớp, nên mình luôn chạy cùng câu lệnh đó mà không có `-delete` trước để xem sẽ xóa gì.

## Lưu trữ và nén

**Nén và giải nén bằng `tar` thế nào?** `tar -czf archive.tar.gz dir/` tạo archive nén gzip, `tar -xzf archive.tar.gz` giải nén, còn `tar -tzf archive.tar.gz` liệt kê nội dung bên trong mà không giải nén. Thêm `v` như `-czvf` chỉ để hiện chi tiết quá trình chạy.

**`df` và `du` khác nhau ở đâu?** `df` báo dung lượng trống và đã dùng theo từng filesystem đã mount, trả lời câu "ổ nào đầy", còn `du` ước lượng dung lượng của file và thư mục, trả lời câu "thư mục nào nặng". Cả hai đều nhận `-h` để hiện số dễ đọc, còn `du -sh dir` cho một con số tổng duy nhất của một đường dẫn.

## Truy cập từ xa và biến môi trường

**Kết nối và cài SSH key thế nào?** `ssh user@host` mở shell từ xa, mặc định dùng port 22 trừ khi server hay config client đổi đi. `ssh-keygen` tạo cặp key, `ssh-copy-id user@host` cài public key lên server, còn các entry trong `~/.ssh/config` lưu sẵn tên host, user, key và port cho từng máy.

**Biến môi trường hoạt động ra sao?** `env` liệt kê các biến hiện tại, `echo $VAR` in giá trị một biến, còn `export VAR=value` đặt biến cho shell hiện tại và các tiến trình con. `~/.bashrc` là nơi Bash interactive đọc lại các thiết lập lặp đi lặp lại, và những biến mình đụng nhiều nhất là `PATH`, `HOME`, `USER` và `SHELL`.

## Lịch trình, gói phần mềm, log và link

**Đọc một entry `cron` thế nào?** `crontab -e` sửa lịch của user hiện tại còn `crontab -l` liệt kê lịch đó. Mỗi dòng có năm trường thời gian — phút, giờ, ngày trong tháng, tháng và ngày trong tuần — rồi tới câu lệnh, với các shorthand như `@reboot`, `@daily` và `@weekly` cho những trường hợp phổ biến.

**Dùng package manager nào ở đâu?** Debian và Ubuntu dùng `apt`, Fedora và các hệ Red Hat hiện nay dùng `dnf` với `yum` giữ lại như alias tương thích, và tất cả đều tự giải quyết dependency. `snap` và `flatpak` đứng bên cạnh như các định dạng độc lập với distro, kèm sandbox mạnh hơn cho ứng dụng.

**Khi có sự cố thì xem log ở đâu?** Log dạng text nằm dưới `/var/log`, tên file cụ thể khác nhau theo distro — ví dụ họ Debian dùng `syslog` và `auth.log` còn họ Red Hat dùng `messages` và `secure`. Trên hệ `systemd` thì `journalctl` truy vấn journal thay cho file rời, còn `tail -f` theo dõi một file đang lớn dần theo thời gian thực.

**Symlink và hard link khác nhau thế nào?** `ln -s target link` tạo symbolic link, một con trỏ tới đường dẫn khác, đi xuyên filesystem được nhưng gãy khi target bị dời. `ln target link` tạo hard link, một tên thứ hai cùng trỏ tới một inode trên cùng filesystem, còn dùng được cho tới khi mọi tên đều bị xóa.

## Điều này đổi lại gì

Đợt ôn này cho mình thấy chỗ nào giải thích được và chỗ nào chỉ mới nhận mặt. Sắp tới mình giữ ba thói quen nhỏ:

- Đọc lại dạng quyền và redirect trước khi dán từ trí nhớ.
- Kiểm tra `systemctl status` kèm `journalctl -u` trước khi cho rằng sửa config thất bại.
- Chạy `find` thử không có `-delete` trước mỗi khi cần xóa.

Các ghi chú này ôn theo [bộ flashcard Linux Fundamentals của devops-daily](https://devops-daily.com/flashcards/linux-fundamentals); phần trả lời phía trên được mình viết lại bằng lời của mình.
