Seorang guru menulis satu soal dan pengerjaannya untuk ditunjukkan kepada murid$subject. Teks di bawah adalah tulisannya, yang sudah ia baca ulang dan benarkan sendiri.

Soal:
$question

Pengerjaan guru:
$steps

Jawaban akhir guru: $final_answer

Kerjakan dalam urutan ini:
1. Kerjakan soal itu sendiri dari awal, tanpa melihat pengerjaan guru. Tulis hasilnya di `our_answer`, sesingkat mungkin.
2. Bandingkan tiap langkah guru dengan hitunganmu, lalu isi `status`:
   - `follows`: langkah itu tepat dan sejalan dengan langkah sebelumnya.
   - `recheck`: kamu bisa menunjuk dengan pasti apa yang berbeda pada langkah itu.
   - `cannot_tell`: kamu tidak yakin, atau langkah itu tidak cukup jelas untuk dibandingkan.
3. Isi `answer`: `follows` jika jawaban akhir guru senilai dengan `our_answer`; `recheck` jika berbeda; `cannot_tell` jika soal tidak lengkap, bermakna ganda, atau jawaban akhir tidak tertulis.

Aturan:
- Cara yang berbeda dari caramu tetapi sah adalah `follows`. Begitu juga bentuk yang senilai, misalnya 6/36 dan 1/6, atau 0,5 dan 1/2.
- Jika ragu, pilih `cannot_tell`. Jangan memilih `recheck` berdasarkan dugaan.
- Tandai `recheck` hanya pada langkah tempat perbedaan itu pertama muncul. Langkah sesudahnya yang hanya meneruskan angka itu diberi `follows`.
- `note` hanya untuk langkah `recheck`: satu kalimat datar yang menyebut apa yang tertulis dan apa hitunganmu, misalnya "Tertulis n(A) = 5, sedangkan hitungan kami mendapat 6 pasangan." Untuk status lain, isi teks kosong.
- `note` akan dibaca oleh guru itu sendiri. Jangan menilai guru, dan jangan memakai kata "salah", "keliru", "kurang", "lemah", atau "seharusnya".
- `n` adalah nomor langkah seperti pada daftar di atas. Beri satu entri untuk setiap langkah.
- Tulis matematika sebagai teks biasa, tanpa LaTeX.
