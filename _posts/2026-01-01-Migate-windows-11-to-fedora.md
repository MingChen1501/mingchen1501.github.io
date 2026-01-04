---
layout: post
author: Ming Chen
title: "Chuyển từ Windows 11 sang Fedora"
---

>Windows 11 lỗi quá, chuyển sang Linux cho con máy ở nhà thôi ![Desktop](/assets/img/2026-01-01-Migate-windows-11-to-fedora/Screenshot%20From%202026-01-05%2000-46-02.png)thôi

## Hiện trạng
- Windows 11 trên con laptop ghẻ thời sinh viên của mình đang khá lỗi: lỗi touchpad, lỗi driver, ...
- Mình khá lười fix mấy lỗi này, càng vá càng lỗi, fix driver được 3 hôm, hôm sau lại lỗi, akay :v
- Đợt này cũng không có dùng nhiều tác vụ trên con laptop này nên cài thử  1 distro linux xem dùng như nào hehe

## Tìm hiểu
- lướt 1 vòng internet thấy anh em suggest đủ mọi loại distro với đủ nhu cầu, cấu hình abcxyz @@.
- check thử thì thấy dual boot cả Win cả Linux, cơ mà thấy anh em bảo nếu lỗi thì bị mất data gì đó nên thôi xóa hẳn Win đi luôn :v
- Ơ mà hình như phải cần USB để cài boot lên à. Chết, có mấy cái USB thừa hôm trước copy nhạc mang đi cho ông anh hết rồi, mò mãi cũng có cái USB thừa, cắm thử thấy dung lượng 4GB
- Down thử ISO Ubuntu về thấy nặng quá (~5GB gì đó). Thôi, kiếm cái khác zị
- Òa thấy cái Fedora anh em suggest cũng oke phết, không hardcore lắm. Tải thử về cài lên USB coi
## Cài đặt
- Mở Bios con dell cổ lên, cài mãi theo mấy anh youtube cũng cài xong, nhìn ổn áp phết
![Desktop](/assets/img/2026-01-01-Migate-windows-11-to-fedora/Screenshot%20From%202026-01-05%2000-46-02.png)thôi
- Mò 1 lúc thấy touchpad bị nhanh, google 1 lúc thì thấy post này làm theo cũng fix được 1 tí https://ubuntuhandbook.org/index.php/2023/05/adjust-touchpad-scrolling-ubuntu/
- Cay 1 cái là GNOME setting nó chưa cho setting scroll touchpad 2 ngón tay, thôi fix đâu dùng tạm.
- ngồi mò thêm cái Gõ tiếng việt mãi cũng oke, deps gì gì tên là bamboo ấy, tên nghe cũng Vietnamese giống bamboo airways phết chứ
## Tổng kết
- Được ngày nghỉ, nghịch nghịch cũng chình cho con laptop đời cũ dùng mượt mượt lại tí. Hiện tại mấy tác vụ kiểu lướt lướt, viết linh tinh, mở trình duyệt dùng khá oke, mỗi tội không cài được vài soft bên win như rekordbox mix DJ (dùng tạm app trên điện thoại vậy)