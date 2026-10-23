---
layout: post
lang: vi
ref: gioi-thieu-ve-internet
date: 2022-12-25
author: Ming Chen
title: "Giải thích về Internet"
tags: [backend-production]
image: /assets/img/2022-12-25-gioi-thieu-ve-internet/al-gore.jpg
description: "Giải thích Internet là gì và cách nó vận hành qua last mile, trung tâm dữ liệu và đường trục, cùng các ứng dụng như web và email."
redirect_from:
  - /2022/12/25/gioi-thieu-ve-internet.html
---

>Internet là mạng máy tính phổ biến nhất thế giới. Nó bắt đầu như một dự án nghiên cứu học thuật vào năm 1969. Và trở thành một mạng lưới thương mại toàn cầu vào những năm 1990. ![Chân dung Al Gore](/assets/img/2022-12-25-gioi-thieu-ve-internet/al-gore.jpg "Ảnh: chân dung chính thức, phạm vi công cộng"){: width="960" height="1200" }

*Cập nhật tháng 10/2026: các số liệu đã được làm mới; nguồn tham khảo liệt kê ở cuối bài. Bài này phỏng theo bài giải thích của Vox năm 2014 (ghi nguồn bên dưới); những đoạn mô tả bối cảnh năm 2014 được giữ lại như tư liệu lịch sử và ghi rõ như vậy.*

## Internet là cái gì ?

Internet là mạng máy tính phổ biến nhất thế giới. Nó bắt đầu như một dự án nghiên cứu học thuật vào năm 1969. Và trở thành một mạng lưới thương mại toàn cầu vào những năm 1990. Ngày nay có khoảng 6 tỷ người dùng internet — chừng ba phần tư nhân loại (ITU, 2025)

Internet đáng chú ý vì tính phi tập trung của nó. Không ai sở hữu internet hoặc kiểm soát những người có thể kết nối với nó. Thay vào đó, hàng ngàn tổ chức khác nhau vận hành mạng lưới của riêng họ và đàm phán các thỏa thuận kết nối tự nguyện.

Hầu hết mọi người truy cập nội dung internet bằng trình duyệt web. Thật vậy, web đã trở nên phổ biến đến mức nhiều người coi internet và web là đồng nghĩa một cách sai lầm. nhưng trên thực tế, web chỉ là một trong nhiều ứng dụng của internet. Các ứng dụng internet phổ biến khác bao gồm email và BitTorrent.

## Internet ở đâu ?

Internet có 3 phần cơ bản:

1) đoạn cuối của kết nối (the last mile) là một phần của internet kết nối các hộ gia đình và doanh nghiệp nhỏ với internet. Khi bài này mới ra đời năm 2014, khoảng 60% kết nối internet dân cư ở Hoa Kỳ chạy trên mạng truyền hình cáp như Comcast và Time Warner Cable, phần còn lại chủ yếu là cáp quang của Verizon FiOS hay U-verse của AT&T. Bức tranh đó giờ đã khác: Time Warner Cable đã sáp nhập vào Charter (Spectrum) từ năm 2016, còn AT&T cũng khai tử thương hiệu U-verse. Tính đến giữa năm 2025, hơn một nửa kết nối cố định ở Mỹ vẫn dùng mạng cáp (đồng trục) như Comcast Xfinity và Charter Spectrum, trong khi gần 3/10 đã chuyển sang cáp quang tới tận nhà như AT&T Fiber và Verizon Fios — còn các đường DSL đồng cũ thì teo dần về con số không (FCC, 2025).
đoạn cuối của kết nối (the last mile) cũng bao gồm các tòa tháp cho phép mọi người truy cập internet bằng điện thoại di động của họ. Dịch vụ internet không dây chiếm một phần lớn và ngày càng tăng trong tất cả việc sử dụng internet
![Sơ đồ đoạn cuối kết nối từ nhà bạn đến nhà mạng](/assets/img/2022-12-25-gioi-thieu-ve-internet/last-mile.jpg){: width="1200" height="800" }

2) trung tâm dữ liệu (Data center) là các phòng chứa đầy máy chủ lưu trữ dữ liệu người dùng và lưu trữ các ứng dụng và nội dung trực tuyến. Một số thuộc sở hữu của các công ty lớn như Google và Meta. Những nơi khác là cơ sở thương mại cung cấp dịch vụ cho nhiều trang web nhỏ hơn. Các trung tâm dữ liệu có kết nối internet rất nhanh, cho phép chúng phục vụ đồng thời nhiều người dùng. Các trung tâm dữ liệu được đặt ở bất cứ đâu trên thế giới nhưng chúng thường đưuọc đặt ở những vùng xa xôi, nơ có giá đất và điện rẻ. Ví dụ: google, Meta, MS đều đã xây dựng các trung tâm dữ liệu rộng lớn ở Lowa.
![Minh họa dãy tủ máy chủ trong trung tâm dữ liệu](/assets/img/2022-12-25-gioi-thieu-ve-internet/data-center.jpg){: width="1200" height="800" }

3)đường trục Internet bao gồm các mạng đường dài, chủ yếu trên cáp quang, mang dữ liệu giữa các trung tâm dữ liệu và người tiêu dùng. Thị trường xương sống có tính cạnh tranh cao. Các nhà cung cấp đường trục thường kết nối các mạng của họ với nhau tại các điểm trao đổi internet, thường nằm ở các thành phố lớn. Thiết lập sự hiện diện tại các IEP giúp các nhà cung cấp dịch vụ xương sống cải thiện kết nối của họ với những người khác dễ dàng hơn nhiều.
![Sơ đồ đường trục cáp quang nối các trung tâm dữ liệu qua điểm trao đổi](/assets/img/2022-12-25-gioi-thieu-ve-internet/duong-truc-backbone.jpg){: width="1200" height="800" }

## Ai đã tạo ra Internet ?

Internet bắt đầu với tên ARPANET, một mạng nghiên cứu học thuật được tài trở bới cơ quan dự án nghiên cứu tiên tiến của quân đội (ARPA, nay là DARPA). Dự án được dẫn dắt bởi Bob Taylor, một quản trị viên ARPA và mạng được xây dựng bởi công ty tư vấn bởi Bolt, Beranek và Newman. Nó bắt đầu hoạt động vào năm 1969.

Năm 1973, các kỹ sư phần mềm Vint Cerf và Bob Kahn bắt đầu làm việc trên thế hệ tiêu chuẩn mạng tiếp theo cho ARPANET. Các tiêu chuẩn này được gọi là TCP/IP, đã trở thành nề tảng của Internet hiện đại, ARPANET chuyển sang sử dụng TCP/IP vào ngày 1 tháng 1 năm 1983.
<figure class="post-figure">
<img src="/assets/img/2022-12-25-gioi-thieu-ve-internet/vint-cerf-bob-kahn.jpg" alt="Vint Cerf và Bob Kahn nhận Huân chương Tự do" width="515" height="328">
<figcaption>Ảnh: Nhà Trắng, phạm vi công cộng</figcaption>
</figure>
Trong những năm 1980, nguồn tài trợ cho internet đã chuyển từ quân đội sang quỹ khoa học quốc gia (NFS). NFS đã tài trợ cho các mạng đường dài đóng vai trò là xương sống của internet từ năm 1981 đến năm 1994. Năm 1994, chính quyền Clinton đã chuyển quyền kiểm soát xương sống của internet cho tư nhân. Nó đã được tư nhân vận hành và tài trợ kể từ đó

## Al Gore (Phó tổng thứ thứ 45 của Hoa kỳ) đã phát minh ra Internet ?

Cựu phó tổng thống AI Gore thường được trích dẫn là đã tuyên bố có công trong việc phát minh ra Internet. Nhưng điều ông thực sự đã nói trong một cuộc phỏng vấn của CNN năm 1999 là “Tôi đã chủ động tạo ra Internet.” Gỏe đã bị chế giễu rộng rãi vì tuyên bố này. Những những người đã phát minh ra internet, các nhà thiết kế TCP/IP Bob Kahn và Vint Cè, đã viết để bảo vệ Gỏe vào năm 2000. Họ lập luận rằng Gỏe là “nhà lãnh đạo chính trị đầu tiên nhận ra tầm quan trọng của internet và thúc đẩy cũng như hỗ trợ sự phát triển của nó.”
<figure class="post-figure">
<img src="/assets/img/2022-12-25-gioi-thieu-ve-internet/al-gore.jpg" alt="Chân dung Al Gore" width="960" height="1200">
<figcaption>Ảnh: chân dung chính thức, phạm vi công cộng</figcaption>
</figure>
“từ những năm 1970 nghị sĩ Gore đã thúc đẩy ý tưởng về viễn thông tốc độ cao,” cặp đôi này đã viết. “Với tư cách là thượng nghị sĩ vào những năm 1980, Gỏe đã thúc giục các cơ quan chính phủ hợp nhất những gì vào thời điểm đó là hàng chục mạng khác nhau và không được kết nồi thành một ‘mạng liên cơ quan’”. Một trong những phương tiện chính là để phổ biến internet ra ngoài lĩnh vực khoa học máy tính.

## Ai điều hành internet ?

Không ai điều hành Internet. Nó được tổ chức như một mạng lưới phi tập trung của các mạng lưới. hàng nghìn công ty, trường học, chính phủ và các thực thể khác vận hành mạng của riêng họ và trao đổi lưu lượng với nhau dựa trên các thỏa thuận kết nối tự nguyện.
Các tiêu chuẩn kỹ thuật dùng chung giúp Internet hoạt động được quản lý bởi một tổ chức có tên là lực lượng đặc nhiệm kỹ thuật internent (Internet engineering task force - IETF). IETF là một tổ chức mở; bất kỳ ai cũng được tự do tham dự các cuộc họp, đề xuất các tiêu chuẩn mới và đề xuất các thay đổi đối với các tiêu chuẩn hiện có. Không ai bắt buộc phải áp dụng các tiểu chuẩn được IETF xác nhận, nhưng quy trình ra quyết định dựa trên sự đồng thuận của IETF giúp đảm bảo rằng các khuyến nghị của nó thường được cộng đồng internet chấp nhận.
![Minh họa cách IETF xây dựng tiêu chuẩn mở](/assets/img/2022-12-25-gioi-thieu-ve-internet/ietf-tieu-chuan.jpg){: width="1200" height="800" }
Tập đoàn cấp số và tên cho Internet (The Internet Corporation for Assigned Names and Numbers - ICANN) đôi khi được mô tả là chịu trách nhiểm quản trị internet. Đúng như tên gọi, ICANN chịu trách nhiệm phân phối tên miền (như mingchen.id.vn) và địa chỉ IP. Nhưng ICANN không kiểm soát ai có thể kết nối với internet hoặc loại thông tin nào có thể được gửi qua internet.
![Minh họa vai trò điều phối tên miền và địa chỉ IP của ICANN](/assets/img/2022-12-25-gioi-thieu-ve-internet/icann-ten-mien-ip.jpg){: width="1200" height="800" }

## Địa chỉ IP (IP address) là gì ?

Địa chỉ giao thức internet là những số mà máy tính sử dụng để nhận dạng nhau trên internet. Ví dụ: địa chỉ IP của vox.com là 216.146.46.10. bộ phận ICANN được gọi là cơ quan cấp số được gán internet chịu trách nhiệm phân phối địa chỉ IP để đảm bảo rằng hai tổ chức khác nhau không sử dụng cùng một địa chỉ.
![Minh họa cách xem địa chỉ IP trên máy tính](/assets/img/2022-12-25-gioi-thieu-ve-internet/dia-chi-ip.jpg){: width="1200" height="800" }

## IPv6 là gì ?

![Sơ đồ cấu trúc địa chỉ IPv6](/assets/img/2022-12-25-gioi-thieu-ve-internet/ipv6.jpg){: width="1200" height="800" }
Tiêu chuẩn internet hiện tại, được gọi là IPv4, chỉ cho phép khoảng 4 tỷ địa chỉ Ip. Đây được coi là một con số rất lớn vào những năm 1970, nhưng ngày nay, nguồn cung cấp địa chỉ IPv4 gần như cạn kiệt.

Vì vậy, các kỹ sư internet đã phát triển một tiêu chuẩn mới gọi là IPv6. IPv6 cho phép lượng địa duy nhất đáng kinh ngạc – con số chính xác dài 39 chữ số- đảm bảo rằng trên thế giới sẽ không bao giờ cạn kiệt nữa.

Lúc đầu, quá trình chuyển đổi sang IPv6 diễn ra chậm. công việc kỹ thuật về tiêu chuẩn đã được hàn thành vào những năm 1990, nhưng cộng đồng internet phải đối mặt với một số vấn đề nghiêm trong về con gà và quả trứng: miễn là hầu hết mọi người sử dùng Ipv4, thì sẽ có rất ít động lực để mọi người chuyển sang IPv6.

Nhưng khi địa chỉ IPv4 trở nên khan hiếm, việc áp dụng IPv6 đã tăng tốc. Tỷ lệ người dùng kết nối với Google qua IPv6 đã tăng từ 1% vào đầu năm 2013 lên 6% vào giữa năm 2015 — và còn tăng tiếp, đến tháng 3/2026 thì lần đầu tiên khoảng một nửa người dùng Google kết nối qua IPv6 (Google, 2026).

## Internet không dây (Wireless) hoạt động như thế nào?

Trong những năm đầu tiên, truy cập internet được truyền qua cáp vật lý. nhưng gần đây, truy cập internet không dây ngày càng trở nên phổ biến.

Có hai loại truy cập internet không dây cơ bản: wifi và di động. mạng wifi thì tương đối đơn giản. bất cứ ai cũng có thể mua thiết bị mạng wifi để cung cấp truy cập internet trong nhà hoặc doanh nghiệp. mạng wifi sử dụng phổ không được cấp phép: tần số điển từ có sẵn cho bất kỳ ai sử dụng miễn phí. Để ngăn các mạng của hàng xóm can thiệp lẫn nhau, thì sẽ có các giới hạn nghiêm ngặt về công suất (phạm vi) của mạng wifi.
![Sơ đồ mạng Wi-Fi trong nhà](/assets/img/2022-12-25-gioi-thieu-ve-internet/wifi-tai-nha.jpg){: width="1200" height="800" }

Mạng di động tập trung hơn. Chúng hoạt động bằng cách chia vùng dịch vụ thành các ô. ở những khu vực đông đúc nhất, các ô có thể nhỏ bằng một khối thành phố; ở các vùng nông thôn một ô có thể dài hàng dặm. mỗi ô có một tháp ở trung tâm cung cấp dịch vụ cho các thiết bị ở đó. khi một thiết bị di chuyển từ ô này sang ô khác, mạng sẽ tự động chuyển thiết bị từ tháp này sang tháp khác, cho phép người dùng tiếp tục liên lạc mà không bị gián đoạn.
![Sơ đồ mạng di động chia ô](/assets/img/2022-12-25-gioi-thieu-ve-internet/mang-di-dong.jpg){: width="1200" height="800" }
Các ô quá lớn để sử dụng năng lượng thấp, không có giấy phép được sử dụng bởi các mạng wifi. Thay vào đó, các mạng di động sử dụng phổ được cấp phép cho việc sử dụng độc quyền của họ. bởi vì quang phổ này khan hiếm nên nó thường được trao bằng hình thức đấu giá. Đấu giá không dây đã được tạo ra doanh thu hàng chục tỷ đô là cho kho bạc hoa kỳ kể từ lần đầu tiên tổ chức vào năm 1994.

## Điện toán đám mây (Cloud) là gì ?

![Sơ đồ điện toán đám mây](/assets/img/2022-12-25-gioi-thieu-ve-internet/dien-toan-dam-may.jpg){: width="1200" height="800" }
điện toán đám mây mô tả một cách tiếp cận điện toán đã trở nên phổ biến vào đầu những năm 2000. Bằng cách lưu trữ tệp trên máy chủ và phân phối phần mềm qua internet, điện toán đám mây cung cấp cho người dùng trải nghiệm điện toán đơn giản hơn, đáng tin cậy hơn. Điện toán đám mây cho phép người tiêu dùng và doanh nghiệp coi điện toán như một tiện ích, để lại các chi tiết kỹ thuật cho các công ty công nghệ.
Ví dụ, vào những nằm 1990, nhiều người đã sử dụng MS office để chỉnh sửa tài liệu và bảng tính. Họ lữu trữ tài liệu trên ổ cứng của họ. và khi một phiên bản mới của MS office được phát hành, khách hàng phải mua nó và cài đặt thủ công trên PC của họ.
Ngược lại, google docs là bộ ứng dụng văn phòng đám mây. Khi người dùng truy cập docs.google.com, họ sẽ tự động nhận được pheiene bản google documents mới nhất. vì các tệp của họ được lưu trữ trên các máy củ của google nên chúng có sẵn trên mọi máy tính. Tuyệt vời hơn nữa, họ không phải lo lắng về việc mất các tệp của mình khi ổ cứng gặp sự cố (Microsoft hiện có bộ ứng dụng văn phòng đám mây riêng có tên là Office 365).
Có rất nhiều ví dụ khác. Gmail và Hotmail là các dịch vụ email trên đám mây đã thay thê phần ớn các ứng dụng email trên bmays tính bàn như Outlook. Dropbox là một dịch vụ điện toán đám mây tự động đồng bộ hóa dữ liệu giữa các thiết bị, giúp mọi người không phải mang các tệp trên đĩa mềm. Icloud của Apple tự động sao chép nhạc của người dùng và các tệp khác từ máy tính để bàn sang thiết bị di động của họ, giúp người dùng không gặp rắc rối khi đồng bộ hóa qua kết nối USB.
Điện toán đám mây cũng có tác động lớn đồi với các doanh nghiệp. vào những năm 1990, các công ty muốn tạo một trang web cần mua và vận hành các máy chủ của riêng họ. nhưng đên năm 2006, amazon.com tung ra amazon web services, cho phép khách hàng thuê máy chủ theo giờ. Điều đó đã hạ tấp rào cản gia nhập để tạo trang web và giúp các trang web nhanh chóng mở rộng dung lượng dễ dang hơn nhiều khi chúng trở nên phổ biến hơn.

## Gói tin (packet) là gì ?

Gói tin là đơn vị cơ bản của thông tin được truyền qua internet. Việc chia thông tin thành các phần nhỏ, để dễ tiêu hóa cho phép sử dụng năng lực của mạng hiệu quả hơn.
Một gói có hai phần. tiêu đề chưa thông tin giúp gói đến đích. Bao gồm độ dài của gói, nguồn và đích đến cảu gói và giá trị tổng kiểm tra giúp người nhận phát hiện xem gói tin có bị hỏng trong quá trình truyền hay không. Sau tiều đề là dữ liệu thực tế. một gói có thể chứa 64kb dữ liệu, tương đương với 20 trang văn bản thuần túy.
Nếu các bộ định tuyến internet gặp phải tắc nghẽn hoặc các sự cố kỹ thuật khác, chúng được phép giải quyết vấn đề đó bằng cách loại bỏ các gói tin. Trách nhiệm của máy tính gửi là phải hiện ra rằng một gói không đến được đích và gửi một bản sao khác. Cách tiếp cận này có vẻ trực giác. Nhưng nó đơn giản hóa cơ sở hạ tầng cốt lõi của internet, dẫn đến hiệu suất cao hơn vỡi chi phí tấp

## World Wide Web (Web) là gì ?

World wide web là một cách phổ biến để xuất bản thông tin trên internet. Web được tạo ra bởi Timothy Berners-Lee, một lập trình viên máy tính tại tổ chức nghiên cứu khoa học châu âu CERN, vào năm 1991. Nó cung cấp một giao diện mạnh mẽ và thân thiện với người dùng hơn các ứng dụng internet khác. Web hỗ trợ các siêu liên kết, cho phép người dùng duyệt từ tài liệu này sang tài liệu khác chỉ bằng một cú nhấp.
<figure class="post-figure">
<img src="/assets/img/2022-12-25-gioi-thieu-ve-internet/tim-berners-lee.jpg" alt="Tim Berners-Lee, cha đẻ của World Wide Web" width="870" height="1200">
<figcaption>Ảnh: Enrique Dans, CC BY 2.0</figcaption>
</figure>
Theo thời gian, web càng ngày càng trở nên tinh vi hơn, hỗ trợ hình ảnh, âm thanh, video và nội dung tương tác. Vào giữa những năm 1990, các công ty như Yahoo và Amazon đã bắt đầu xây dựng các hoạt đông kinh doanh có lợi nhuận dựa trên web. Vào những năm 2000, các ứng dụng dựa trên web đầy đủ tính năng như Yahoo Maps và Google Docs đã được tạo ra.
Năm 1994, Berners-Lee thành lập world wide web consortium (W3C) để trở thành tổ chức tiêu chuẩn chính thức của web. Ông vẫn là giám đốc của w3c và tiếp tục giám sát sự phát triển của các tiêu chuẩn web. Tuy nhiên, web là một nền tảng mở và w3c không thể bắt buộc bất kỳ ai chấp nhận các đề xuất của nó. Trên thực tế, các tổ chức có ảnh hưởng lớn nhất đối với web là Microsoft, Google, Apple, Mozilla, những công ty sản xuất các trình duyệt web hàng đầu. bất kỳ công nghệ nào được áp dụng bởi bốn công ty này đều trở thành tiêu chuẩn của web trên thực tế.
Web đã trở nên phổ biến dến mức nhiều người hiện coi nó đồng nghĩa với chính interner. Nhưng về mặt kỹ thuật, web chỉ là một trong nhiều ứng dụng của internet. Các ứng dụng khác bao gồm email và bittorent.

## Trình duyệt web là gì ?

Trình duyệt web là một chương trình máy tính cho phép người dùng tải xuống và xem các trang web. Trình duyết có sẵn cho máy tính để bàn, máy tính bảng, và điện thoại di dộng.
![Minh họa trình duyệt Mosaic năm 1993](/assets/img/2022-12-25-gioi-thieu-ve-internet/trinh-duyet-dau-tien.jpg){: width="1200" height="800" }
Trình duyệt được sử dụng rộng rãi đầu tiên là Mosaic. Do các nhà nghiên cứu tại đại học Illinois tạo ra. Nhóm Mosaic đã chuyển đến california để thành lập netscape, công ty đã xây dựng trình duyệt web thành công về mặt thương mại đầu tiên vào năm 1994.
![Minh họa lại cửa sổ trình duyệt Mosaic](/assets/img/2022-12-25-gioi-thieu-ve-internet/mosaic-minh-hoa.jpg){: width="1200" height="800" }
![Minh họa lại trình duyệt Netscape Navigator](/assets/img/2022-12-25-gioi-thieu-ve-internet/netscape-minh-hoa.jpg){: width="1200" height="800" }
Sự phổ biến của Netscape đã sớm bị IE của Microsoft làm lu mờ, nhưng một phiên bản mã nguồn mở của trình duyệt Netscape đã trở thành trình duyệt Firefox hiện đại. Apple phát hành trình duyệt Safari vào năm 2003, và Google đã phát hành trình duyệt có tên Chrome vào năm 2008. Rồi Chrome vươn lên thống trị: tính đến cuối năm 2026, Chrome chiếm khoảng hai phần ba lượt dùng trình duyệt toàn cầu, tiếp theo là Safari với chưa đầy một phần năm, còn Edge và Firefox chia nhau phần lớn số còn lại (Statcounter, tháng 9/2026). Microsoft đã khai tử Internet Explorer từ tháng 6/2022 và hướng người dùng sang Edge (Microsoft, 2022)
![Dòng thời gian các trình duyệt web](/assets/img/2022-12-25-gioi-thieu-ve-internet/cuoc-dua-trinh-duyet.jpg){: width="1200" height="800" }

## TLS là gì (và SSL là gì) ?

TLS là viết tắt của Transport Layer Security — họ công nghệ mã hóa giúp người dùng web bảo vệ quyền riêng tư của thông tin mình truyền qua internet. Còn "SSL" (Secure Sockets Layer) chỉ là tên gọi cũ của cùng họ công nghệ này: SSL 3.0 đã bị khai tử chính thức từ năm 2015 sau khi vụ tấn công POODLE cho thấy nó hỏng từ gốc (IETF RFC 7568), và kẻ kế nhiệm là TLS — bản 1.3, chuẩn mới nhất, được chuẩn hóa năm 2018 (IETF RFC 8446) và sửa đổi năm 2026 (IETF RFC 9846) — mới là thứ thực sự bảo vệ kết nối của bạn hôm nay, dù ngoài miệng người ta vẫn quen gọi là "SSL".
Khi bạn truy cập một trang web an toàn chẳng hạn như gmail.com bạn sẽ thấy một ổ khóa bên cạnh URL. Nó cho biết rằng thông tin liên lạc của bạn với trang web đã được mã hóa. Đây là giao diện trong trình duyệt chrome của google.
![Minh họa ổ khóa HTTPS và kết nối được mã hóa](/assets/img/2022-12-25-gioi-thieu-ve-internet/ssl-https.jpg){: width="1200" height="800" }

Khóa đó được cho là báo hiệu rằng các bên thứ ba sẽ không thể đọc bất kỳ thông tin nào bạn gửi hoặc nhận. về cơ bản, TLS thực hiện điều này bằng cách chuyển đổi dữ liệu của bạn thành một thông điệp đã được mã hóa mà chỉ người nhận mới biết cách giải mã. Nếu một kẻ xấu đang nghe lén cuộc hội thoại, nó sẽ chỉ thấy một chuỗi ký tự có vẻ như ngẫu nhiên chứ không phải nội dung email, bài đăng trên Facebook, số thẻ tín dụng hay thông tin cá nhân khác của bạn.
Netscape giới thiệu SSL vào năm 1994. Những năm đầu, nó chỉ được dùng trên một số loại trang web, chẳng hạn các trang ngân hàng trực tuyến. Đầu những năm 2010, Google, Yahoo và Facebook đều chuyển trang web và dịch vụ của mình sang kết nối mã hóa, và phong trào mã hóa toàn diện sau đó đã thắng: ngày nay trình duyệt gắn nhãn "Không bảo mật" cho các trang HTTP trần, và đại đa số lưu lượng web đã được mã hóa (Google Transparency Report, 2026).

## DNS là gì ?

DNS - Domain Name System - Hệ thống phân giải tên miền là lý do bạn có thể truy cập mingchen bằng cách nhập mingchen.id.vn vào trình duyệt của mình thay vì một địa chỉ số khó nhớ, chẳng hạn như 216.146.46.10.
Hệ thống có thứ bậc. ví dụ: tên miền .com được quản lý bởi một công ty có tên là Verisign. Verisign chỉ định các tên miền phụ như google.com và facebook.com. ngược lại, chủ sở hữu các miền cấp hai này có thể tạo các miền phụ như mail.google.com và maps.google.com.
Bởi vì các trang web phổ biến dùng tên miền để tự nhận diện công khai, nên tính bảo mật của DNS ngày càng được quan tâm. Tội phạm cũng như gián điệp chính phủ từng tìm cách phá DNS để mạo danh các trang phổ biến như facebook.com hay gmail.com rồi chặn đọc liên lạc riêng tư của họ. Một chuẩn có tên DNSSEC ra đời để tăng cường bảo mật DNS bằng chữ ký mật mã. Phần nền móng giờ đã xong — hầu như mọi tên miền cấp cao nhất đều đã được ký — nhưng việc áp dụng vẫn còn dở dang: chỉ khoảng một phần ba máy phân giải trên thế giới kiểm tra chữ ký, và trong các tên miền lớn như .com thì chỉ một tỉ lệ một chữ số tên miền được ký (APNIC Labs, ICANN ITHI, 2025–2026).
![Sơ đồ phân cấp hệ thống tên miền DNS](/assets/img/2022-12-25-gioi-thieu-ve-internet/dns.jpg){: width="1200" height="800" }

## Ai quyết định tên miền nào tồn tại và ai có được chúng ?

Hệ thống tên miền được quản lý bởi ICANN – một tổ chức phi lợi nhuận có trụ sở tại california. ICANN được thành lập vào năm 1998. Nó được bộ thương mại hoa kỳ cấp quyền đối với DNS, mặc dù nó ngày càng khẳng định sự độc lập của mình với chính phủ hoa kỳ.
Có hai loại tên miền. đầu tiên là tên miền chung cao cấp nhất (gTLDs - generic Top level Domains). chẳng hạn như .com .edu .org .gov. bởi vì internet bắt nguồn từ hoa kỳ nên những miền này có xu hướng phổ biến nhất ở đó. Quyền đối với các miền này thường là đưuọc ủy  quyền cho các tổ chức tư nhân.
![Minh họa các tên miền chung cấp cao](/assets/img/2022-12-25-gioi-thieu-ve-internet/ten-mien-gtld.jpg){: width="1200" height="800" }
Ngoài ra còn có các tên miền cấp cao nhất theo mã quốc gia (ccTLDs - country-code top-level domains). Mỗi quốc gia trên thế giới đều có mã gồm 2 chữ cái riêng, ví dục ccTLD của hoa kỳ là .us, vương quốc anh là .uk, trung quốc là .cn. các miền này đưuọc quản lý bởi các cơ quan có thẩm quyền ở mỗi quốc gia. Một số ccTLD chẳng hạn như .tv (dành cho quốc đảo Tuvalu) và .io (lãnh thổ ấn độ dương thuộc anh), đã trở nên phổ biến để sử dụng bên ngoài quốc gia của họ.
![Minh họa các tên miền quốc gia](/assets/img/2022-12-25-gioi-thieu-ve-internet/ten-mien-cctld.jpg){: width="1200" height="800" }
Vào năm 2011, ICANN đã bỏ phiếu để việc tạo gTLD mới dễ dàng hơn. Đợt đăng ký 2012 sau đó đã bổ sung hơn 1.200 tên miền mới vào không gian tên internet — mà câu chuyện chưa dừng ở đó: đợt đăng ký thứ hai khép lại vào tháng 8/2026 với hơn 1.600 hồ sơ đang được xét duyệt (ICANN, 2026).

## Nguồn

[Vox](https://www.vox.com/2014/6/16/18076282/the-internet)

*Nguồn ảnh: ảnh Al Gore là chân dung chính thức của Phó Tổng thống Hoa Kỳ (1994, phạm vi công cộng); ảnh Vint Cerf và Bob Kahn là ảnh Nhà Trắng của Paul Morse (2005, phạm vi công cộng); ảnh Tim Berners-Lee của Enrique Dans ([CC BY 2.0](https://creativecommons.org/licenses/by/2.0/)) — cả ba qua Wikimedia Commons. Các sơ đồ còn lại do tác giả tự vẽ.*

### Nguồn cho đợt làm mới tháng 10/2026 (truy cập ngày 22/10/2026)

- [ITU Facts and Figures 2025: tình hình dùng internet](https://www.itu.int/itu-d/reports/statistics/2025/10/15/ff25-internet-use/) — khoảng 6 tỷ người online năm 2025.
- [FCC Internet Access Services, số liệu đến 30/6/2025](https://www.fcc.gov/document/internet-access-services-status-june-30-2025) — kết nối cố định theo công nghệ (cáp 55,2%, quang 28,5%).
- [Charter hoàn tất sáp nhập Time Warner Cable và Bright House, 2016](https://ir.charter.com/news-releases/news-release-details/charter-communications-time-warner-cable-and-bright-house/) — Time Warner Cable về với Charter (Spectrum).
- [AT&T khai tử thương hiệu U-verse cho Internet và điện thoại, 2016](https://www.nexttv.com/news/att-readies-u-verse-brand-ether-407876); [AT&T ngừng bán U-verse TV, 2020](https://www.nexttv.com/news/att-stops-selling-u-verse-tv).
- [Statcounter: thị phần trình duyệt toàn cầu, tháng 9/2026](https://gs.statcounter.com/browser-market-share) — Chrome khoảng hai phần ba, Safari chưa đầy một phần năm.
- [Microsoft: Internet Explorer 11 nghỉ hưu ngày 15/6/2022](https://blogs.windows.com/windowsexperience/2022/06/15/internet-explorer-11-has-retired-and-is-officially-out-of-support-what-you-need-to-know/).
- [IETF RFC 7568: khai tử SSLv3 (2015)](https://www.rfc-editor.org/info/rfc7568/) và [IETF RFC 8446: TLS 1.3 (2018)](https://www.rfc-editor.org/info/rfc8446/), được sửa đổi bởi [IETF RFC 9846: TLS 1.3 (2026)](https://www.rfc-editor.org/info/rfc9846/).
- [Google Transparency Report: mã hóa HTTPS trên web](https://transparencyreport.google.com/https/overview?hl=en) — khoảng 95% trở lên số trang tải trong Chrome dùng HTTPS.
- [Thống kê IPv6 của Google](https://www.google.com/intl/en/ipv6/statistics.html) — khoảng một nửa người dùng Google dùng IPv6 năm 2026.
- [ICANN: đợt gTLD mới 2026 khép lại với 1.616 hồ sơ được xét](https://www.icann.org/en/announcements/details/icann-confirms-number-of-applications-proceeding-in-the-2026-round-22-09-2026-en); [đợt 2012 bổ sung hơn 1.200 gTLD](https://newgtldprogram.icann.org/en/application-rounds/round2/agb).
- [APNIC Labs: tỉ lệ kiểm tra DNSSEC](https://stats.labs.apnic.net/dnssec/) và [ICANN ITHI Metric M11 (triển khai DNSSEC)](https://observatory.research.icann.org/graph-m11.html) — khoảng một phần ba máy phân giải kiểm tra; tỉ lệ tên miền được ký chỉ một chữ số.
