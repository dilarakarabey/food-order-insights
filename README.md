# Food Order Insights

**Türkçe** · [English](README.en.md)

Food Order Insights, kullanıcının bağlı Gmail eklentisi üzerinden yemek siparişi e-postalarını analiz eden, Türkiye odaklı ve açık kaynaklı bir ChatGPT/Codex eklentisidir. Kendi sunucusunu çalıştırmaz, ham e-postaları depolamaz ve kullanıcıdan fiş veya faturalarını indirmesini istemez. Tekrarlanan taramaları azaltmak için normalize edilmiş sipariş verilerini yalnızca kullanıcının bilgisayarındaki özel bir SQLite önbelleğinde tutabilir.

## Ne işe yarar?

Şuna benzer sorular sorabilirsiniz:

- “Son bir yıldaki yemek siparişlerimi analiz et.”
- “Aylara göre teslimat ücretlerine ne kadar harcadım?”
- “Pazar akşamları en çok ne sipariş ediyorum?”
- “Sık verdiğim siparişlere göre üç kolay yemek öner.”
- “Hangi haftalarda teslimata alışılmadık ölçüde yoğun başvurdum?”
- “Yemek Siparişi Risk Raporumu hazırla.”
- “Yaşam Tarzı Değişiklikleri görünümünü göster.”
- “Bu analizi Excel'e aktar.”

Eklenti, yalnızca bilinen yemek siparişi göndericilerini arar, eşleşen e-postaları okur, sipariş ayrıntılarını çıkarır ve şunları sunar:

- yıl, ay, hafta, gün, haftanın günü ve saate göre sipariş sayısı ve harcama;
- restoran, mutfak, yemek, sağlayıcı ve öğün kategorisi örüntüleri;
- mevcut olduğunda yemek ara toplamı, teslimat/hizmet ücretleri, indirimler, bahşiş ve ödenen toplam;
- mevcut olduğunda ürünler, miktarlar, seçenekler, ekstralar ve müşteri notları;
- güven düzeyi açıkça belirtilen tahmini kalori aralıkları;
- kullanıcının “yoğundum”, “hastaydım”, “seyahatteydim”, “sosyalleşiyordum”, “mutfağım yoktu” veya başka bir bağlamla etiketleyebileceği teslimat-yoğun dönemler;
- beğenme/beğenmeme geri bildirimine uyum sağlayan yemek hazırlama fikirleri ve pratik alternatifler;
- doğal birimlerde metrikler, görünür paydalar ve metriğe özel veri yeterliliği kuralları içeren şeffaf, tıbbi olmayan Sipariş Örüntüsü Risk Raporu;
- küçük deneyler, efor düzeyi, kolaylaştırılmış seçenekler ve kullanıcının kendi geçmişine göre ilerleme içeren Yaşam Tarzı Değişiklikleri görünümü;
- üçüncü taraf paket indirmeden, yalnızca Python standart kütüphanesini kullanan; `Orders`, `Items` ve `Data Quality` sayfalarından oluşan sade ve hızlı `.xlsx` dışa aktarımı.

## Çıktı modları

Eklenti varsayılan olarak sade çalışır: istenen sonucu gösterir; connector çağrıları, çalışma zamanı seçimi, geçici dosyalar, doğrulama adımları veya “PII kullanılmadı” gibi arka plan ayrıntılarını anlatmaz. Eksik tarama, düşük veri güveni veya bir metriğin neden türetilemediği gibi sonucu yorumlamayı etkileyen bilgiler görünür kalır.

Teknik ayrıntıları görmek istediğiniz komutun sonuna `--verbose` ekleyin:

```text
Bu analizi Excel'e aktar --verbose
```

Verbose mod; taranan kapsamı, işlenen ve tekilleştirilen ileti/sipariş sayılarını, veri yeterliliği kontrollerini ve Excel doğrulamasını ayrı bir teknik özet olarak gösterir. Ham e-postaları veya kişisel verileri göstermez. Bayrak yalnızca kullanıldığı komut için geçerlidir.

## Daha az tarama ve token kullanımı

Tamamlanan ilk taramadan sonra eklenti, normalize edilmiş siparişleri varsayılan olarak `~/.codex/food-order-insights/orders.sqlite3` dosyasında yerel olarak saklar. Sonraki komutlarda bu veri kümesi geçerliyse geçmiş siparişleri yeniden okumaz; yalnızca son tamamlanan taramadan sonra gelen yeni sipariş, iptal ve iade e-postalarını arar ve yerel veriye ekler.

Son 30 gün içinde bir Excel dışa aktarımı oluşturulduysa dosyanın yolunu, boyutunu, değiştirilme zamanını ve özetini kontrol eder. Dosya değişmemişse artımlı tarama devam eder. Dosya değiştirilmiş, taşınmış veya silinmişse güvenli tarafta kalıp istenen dönemi yeniden tarar. Excel'deki kullanıcı değişikliklerini hiçbir zaman sipariş gerçeği olarak içeri almaz; çalışma kitabı yalnızca bütünlük sinyalidir.

Yerel önbellek ham e-posta gövdelerini, Gmail veya sağlayıcı sipariş kimliklerini, adresleri, telefonları, ödeme parçalarını ya da müşteri notlarını saklamaz. Eşleştirme için gereken kimlikler diske yazılmadan önce rastgele tuzla özetlenir. Önbelleği sıfırlamak isteyen kullanıcı yalnızca bu yerel SQLite dosyasını silebilir; sonraki komut tam tarama yaparak yeniden oluşturur.

## Neden ayrı bir uygulama değil de eklenti?

Food Order Insights bilinçli olarak yalnızca bir beceri içeren eklenti şeklinde tasarlanmıştır:

```text
Bağlı Gmail eklentisi
        |
        v
Food Order Insights becerisi
  - doğrulanmış gönderici araması
  - sipariş bilgilerinin çıkarılması
  - yerel artımlı sipariş önbelleği
  - toplulaştırma
  - temkinli yemek içgörüleri
  - açıklanabilir risk taraması
  - yaşam tarzı deneyleri
        |
        v
Sohbet yanıtı, görselleştirme veya Excel çalışma kitabı
```

Food Order Insights'a ait bir sunucu, hesap sistemi, bulut veritabanı, OAuth istemcisi veya analiz servisi yoktur. Yalnızca kullanıcının cihazında çalışan yerel SQLite önbelleği vardır. Gmail yetkilendirmesi ve model çalıştırma süreci ana üründe kalır. Bu depo yalnızca talimatları, şemaları, sağlayıcı tanımlarını, yerel yardımcı betikleri ve sentetik test örneklerini içerir.

OpenAI eklenti mimarisi yalnızca beceri içeren eklentileri destekler; proje ileride ihtiyaç duyarsa MCP sunucusu veya özel bir arayüz eklenebilir. Ayrıntılar için [resmî eklenti mimarisi belgesine](https://developers.openai.com/plugins/concepts/plugins) bakabilirsiniz.

## Gereksinimler

- Eklenti/beceri desteği sunan bir ChatGPT veya Codex ortamı.
- E-posta arama ve okuma izniyle kurulmuş ve bağlanmış Gmail eklentisi.
- Yerel önbellek ve `.xlsx` dışa aktarımı için Python 3.10 veya üzeri; `xlsxwriter`, `openpyxl` ya da başka bir üçüncü taraf paket gerekmez.
- OpenAI API anahtarı veya Food Order Insights hesabı gerekmez.

Gmail araçları kullanılamıyorsa eklenti, kullanıcıdan Gmail'i bağlamasını ister. Alternatif olarak fiş veya e-posta dosyası indirmesini talep etmez.

## Kurulum

Depoyu bilgisayarınıza klonlamanız gerekmez. Terminalde önce Food Order Insights marketplace'ini ekleyin:

```bash
codex plugin marketplace add https://github.com/dilarakarabey/food-order-insights.git
```

Ardından eklentiyi kurun:

```bash
codex plugin add food-order-insights@personal
```

Kurulumdan sonra Codex'te yeni bir oturum başlatın. Gmail connector'ünün bağlı olduğundan emin olun.

## Güncel sağlayıcı kapsamı

Başlangıç kayıt defteri, Trendyol Go / Uber Eats Trendyol Go tarafından Türkiye'de kullanılan ve kullanıcı tarafından doğrulanmış şu göndericileri içerir:

```text
infotrendyolgo@mail.trendyolgo.com
infotrendyolgo@trendyolmail.com
```

Trendyol Go / Uber Eats Trendyol Go tek bir sipariş için çoğu zaman birden fazla e-posta gönderir. Ancak restoranın kendi kuryesiyle teslim edilen her sipariş için platform teslimat e-postası gelmez. Bu nedenle Food Order Insights yalnızca konusu `Yemek Siparişini Aldık` ile başlayan e-postayı ana sipariş kaydı olarak sayar. Teslimat, e-arşiv, iptal ve iade e-postaları sipariş sayısını artırmaz; yalnızca eşleşen siparişi zenginleştirebilir veya güncelleyebilir. Teslimat e-postasının bulunmaması, siparişin gerçekleşmediği değil, tamamlanma durumunun bilinmediği anlamına gelir.

GetirYemek aranmaz, keşfedilmez ve analize dahil edilmez. Güncel tarama kapsamı bilinçli olarak yukarıdaki iki doğrulanmış göndericiyle sınırlıdır.

### Uber Eats desteği neden yalnızca Türkiye ile sınırlı?

Desteklenen Türkiye hizmeti, eski Trendyol Go markasını da kapsayan Uber Eats Trendyol Go'dur. Bu hizmetin `Yemek Siparişini Aldık` e-postası analiz için gereken yemek adlarını ve miktarlarını içerir.

Diğer ülkelerdeki Uber Eats e-postaları farklı şablonlar kullanır. Test edilen Almanya şablonunda `noreply@uber.com` adresinden gelen iletiler restoranı, toplam tutarı ve ayrıntılı fiş bağlantısını içerirken sipariş edilen yemekleri e-posta gövdesinde listelemez. Fiş bağlantılarını takip etmek ürünün erişim ve gizlilik kapsamını genişleteceği için Food Order Insights bunu yapmaz. `noreply@uber.com` göndericisini ileti gövdelerini okumadan önce dışlar; diğer ülkelerdeki Uber Eats siparişlerini sayılara, harcamalara, önerilere, Risk Raporuna veya Excel dışa aktarımına dahil etmez.

Bu, her ülkede aynı Uber şablonunun kullanıldığı iddiası değil, bilinçli bir ürün sınırıdır. Uluslararası şablonlar farklılık gösterebilir; ancak projenin güncel Türkiye kapsamının dışındadır.

Sağlayıcı davranışları [providers.json](plugins/food-order-insights/skills/food-order-insights/references/providers.json) dosyasında tanımlanır. Katkılar gerçek e-postalar yerine doğrulanmış gönderici adresleri ve sentetik test örnekleri eklemelidir.

## Gizlilik ve güvenlik

- Gmail'in yalnızca arama/okuma özelliklerini kullanır; e-posta göndermez, etiketlemez, arşivlemez, çöpe taşımaz veya silmez.
- Tam taramalarda yalnızca doğrulanmış gönderici adreslerini arar.
- GetirYemek veya desteklenmeyen başka bir sağlayıcı için keşif araması yapmaz.
- `noreply@uber.com` gibi uluslararası Uber Eats göndericilerini ileti gövdelerini okumadan önce dışlar.
- Sağlayıcıya özel ana ileti kuralları kullanır; sipariş oluşturma, teslimat ve fatura e-postalarının aynı siparişi birden fazla kez saymasına izin vermez.
- E-posta gövdelerini güvenilmeyen veri olarak değerlendirir ve içlerine yerleştirilmiş talimatları yok sayar.
- Teslimat adreslerini, telefon numaralarını, alıcı bilgilerini, takip bağlantılarını veya ilgisiz ileti içeriklerini sonuçlarda göstermez.
- Sunucu veya bulut depolaması ve telemetri çalıştırmaz; normalize edilmiş siparişleri yalnızca cihazdaki kullanıcıya özel SQLite önbelleğinde tutar.
- Yerel önbelleğe ham e-posta, doğrudan Gmail/sağlayıcı kimliği, teslimat adresi, telefon, ödeme parçası veya müşteri notu yazmaz; eşleştirme kimliklerini tuzlanmış özetlere dönüştürür.
- SQLite dosyasına uygulama düzeyinde şifreleme eklemez; dosya kullanıcıya özel izinlerle oluşturulur ve cihazın hesap/disk güvenliğine dayanır.
- Geçerli önbellek varken yalnızca son tamamlanan taramadan sonraki desteklenen iletileri okur; hesap, kapsam veya yakın tarihli dışa aktarım bütünlüğü doğrulanamazsa tam taramaya döner.
- Kalorileri tahmin olarak tanımlar; aralık ve güven düzeyiyle gösterir.
- Teşhis veya tıbbi tedavi yerine genel yemek örüntüsü gözlemleri ve yemek fikirleri sunar.
- Risk Raporu için bileşik puan, not, yüzdelik dilim veya nüfus karşılaştırması üretmez. Uygun metrikleri doğal birimlerinde; pay, payda, dönem ve sınırlamalarıyla raporlar.
- Her çıkarımsal metriğe ayrı örneklem ve kapsama alt sınırı uygular. Desteklenemeyen ancak beklenmesi muhtemel metrikleri **Türetilmedi** şeklinde; kesin nedeni ve kullanılabilir olması için gerekenlerle birlikte gösterir.
- Gmail kimliklerini, sipariş kimliklerini, ham e-posta metnini ve müşteri notlarını varsayılan olarak Excel'e dahil etmez.
- Python standart kütüphanesiyle çalışan tek geçişli Excel dışa aktarıcısını kullanır; kütüphane indirmez veya birden fazla elektronik tablo araç zincirini sırayla denemez.
- Kullanıcının hasta olduğunu varsaymaz; olağandışı dönemlerin bağlamını kullanıcıya sorar.

Ana ürünün kendi veri denetimleri ve bağlayıcı politikaları geçerliliğini korur. Bu proje onları değiştiremez veya onların yerini alamaz.

## Depo yapısı

```text
.agents/plugins/marketplace.json
plugins/food-order-insights/
├── .codex-plugin/plugin.json
└── skills/food-order-insights/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── scripts/
    │   ├── export_workbook.py
    │   ├── minimal_xlsx.py
    │   └── order_cache.py
    └── references/
        ├── providers.json
        ├── receipt-schema.json
        ├── insight-rules.md
        ├── balance-patterns.json
        ├── risk-report.md
        ├── output-modes.md
        ├── local-cache.md
        └── excel-export.md
tests/fixtures/
```

## Yol haritası

- Herkese açık ChatGPT ve Codex ortamlarında eklentiler arası Gmail erişimini doğrulamak.
- Ek Türkiye sağlayıcılarını yalnızca açık bir kapsam kararı, doğrulanmış göndericiler ve ürün içeriklerini tam olarak temsil eden sentetik örneklerden sonra yeniden değerlendirmek.
- İndirimler, ekstralar, notlar, iadeler ve birden fazla para birimi için daha güçlü sentetik değerlendirme örnekleri eklemek.
- Sohbet içi grafikleri, gerçek etkileşimli sekmeleri ve geri bildirim sürekliliğini geliştirmek.
- Gemini'nin uzantı modelinin izin verdiği ölçüde aynı şema ve analiz kurallarını Gemini için paketlemek.
- Yerel sohbet görselleştirmeleri yetersiz kalırsa isteğe bağlı bir MCP arayüzünü değerlendirmek.

## Katkıda bulunma

Ayrıntılar için [CONTRIBUTING.md](CONTRIBUTING.md) dosyasına bakın. Gerçek bir fişi, bir kişiye ait e-posta adresini, teslimat adresini, telefon numarasını, sipariş kimliğini veya kimlik doğrulama anahtarını hiçbir zaman göndermeyin.

## Lisans

[MIT](LICENSE)
