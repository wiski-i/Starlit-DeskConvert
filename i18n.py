"""English and Turkish strings for DeskConvert."""

from __future__ import annotations

LANGUAGES = {"tr": "Türkçe", "en": "English"}
DEFAULT_LANGUAGE = "tr"
_language = DEFAULT_LANGUAGE

_TURKISH = {
    "Language": "Dil",
    "Could not save the language preference.": "Dil tercihi kaydedilemedi.",
    "File converter · Images, video, audio, documents and archives": (
        "Dosya dönüştürücü · Görsel, video, ses, belge ve arşiv"
    ),
    "Drop files here": "Dosyaları buraya sürükleyip bırakın",
    "Choose files to convert": "Dönüştürmek için dosya seçin",
    "Choose files": "Dosya Seç",
    "Preview": "Önizleme",
    "Expand": "Büyüt",
    "Choose a file": "Bir dosya seçin",
    "Queue": "Kuyruk",
    "Clear": "Temizle",
    "Clear completed": "Tamamlananları kaldır",
    "Target format": "Hedef format",
    "Compatible formats appear here.": "Dosyaya uygun formatlar burada görünür.",
    "Save method": "Kaydetme yöntemi",
    "Create a copy": "Kopya oluştur",
    "Replace original": "Orijinalin yerine koy",
    "Choose folder": "Klasör seç",
    "Same folder as the source": "Kaynakla aynı klasör",
    "Convert": "Dönüştür",
    "Show output": "Çıktıyı göster",
    "Show error": "Hatayı göster",
    "Could not locate the output file.": "Çıktı dosyası bulunamadı.",
    "Stop after this file": "Bu dosyadan sonra dur",
    "Stopping…": "Durduruluyor…",
    "Finishing the current file before stopping.": "Durdurmadan önce sıradaki dosya tamamlanıyor.",
    "Stopped · {done}/{total} files processed": "Durduruldu · {done}/{total} dosya işlendi",
    "Waiting for files…": "Dosya bekleniyor…",
    "Main context menu enabled": "İlk sağ tık menüsü açık",
    "Context menu enabled": "Sağ tık menüsü açık",
    "Add to context menu": "Sağ tık menüsüne ekle",
    "File Explorer context menu": "Sağ tık menüsü",
    "Convert File": "Dosya Dönüştür",
    "Context menu command removed.": "Sağ tık komutu kaldırıldı.",
    "Main context menu → {command}": "İlk sağ tık menüsü → {command}",
    "Show more options → {command}": "Daha fazla seçenek göster → {command}",
    "Choose an output folder": "Çıktı klasörü seçin",
    "The original goes to the Recycle Bin": "Orijinal Geri Dönüşüm Kutusu’na gider",
    "Queue cleared.": "Liste temizlendi.",
    "No files added yet": "Henüz dosya eklenmedi",
    "Not available": "Kullanılamıyor",
    "Unsupported format": "Tanınmayan format — dönüştürülemiyor",
    "{count} frames": "{count} kare",
    "1 file ready": "1 dosya hazır",
    "{count} files ready": "{count} dosya hazır",
    "No compatible files": "Uygun dosya yok",
    "WebP cannot preserve the color depth of a 16-bit PNG.": "WebP, 16 bit PNG’nin renk derinliğini koruyamaz.",
    "Lossless WebP conversion does not support animated PNGs.": (
        "Hareketli PNG için kayıpsız WebP dönüşümü desteklenmiyor."
    ),
    "Only the first frame or page is included.": "Animasyondan veya çok sayfalı görselden ilk kare alınır.",
    "Lossless WebP · Verifies 8-bit pixels and transparency.": (
        "Kayıpsız WebP · 8 bit pikseller ve saydamlık doğrulanır."
    ),
    "No audio · 256 colors · 12 fps · Up to 480 px wide.": (
        "Ses çıkarılır · 256 renk · 12 kare/sn · En fazla 480 px genişlik."
    ),
    "Only the audio track is included.": "Ses parçası alınır. Görüntü çıktı dosyasına eklenmez.",
    "Compatible streams are copied without re-encoding.": "Uyumlu akışlar yeniden kodlanmadan kopyalanır.",
    "JPEG is lossy. Transparent areas get a white background.": (
        "JPEG kayıplıdır. Saydam alanlar beyaz zeminle birleştirilir."
    ),
    "PNG inputs use lossless encoding. Other images use high quality.": (
        "PNG girişleri kayıpsız, diğer görseller yüksek kalitede kodlanır."
    ),
    "Output format · {format}": "Çıktı biçimi · {format}",
    "Convert {count} file(s)? After the output is verified, the original goes to the Recycle Bin.": (
        "{count} dosyayı dönüştürmek istiyor musunuz? Çıktı doğrulandıktan sonra "
        "orijinal dosya Geri Dönüşüm Kutusu’na taşınır."
    ),
    "Converting…": "Dönüştürülüyor…",
    "Output saved. The original was kept.": "Çıktı kaydedildi. Orijinal korundu.",
    "Original kept. {reason}": "Orijinal korundu. {reason}",
    "Conversion could not be completed.": "Dönüşüm tamamlanamadı.",
    "Saved · {filename}": "Kaydedildi · {filename}",
    "{done}/{total} files converted": "{done}/{total} dosya dönüştürüldü",
    "1 warning": "1 uyarı",
    "{count} warnings": "{count} uyarı",
    "Output folder": "Çıktı klasörü",
    "Wait for the conversion to finish before closing the window.": (
        "Pencereyi kapatmak için dönüşümün tamamlanmasını bekleyin."
    ),
    "Close": "Kapat",
    "Preparing preview…": "Önizleme hazırlanıyor…",
    "Preview is unavailable for this file.": "Bu dosyanın önizlemesi açılamadı.",
    "Silent video preview · up to 60 sec": "Sessiz video önizlemesi · en fazla 60 sn",
    "Audio preview": "Ses önizlemesi",
    "First 45 seconds": "İlk 45 saniye",
    "No content to show.": "Gösterilecek içerik yok.",
    "Could not prepare the audio preview.": "Ses önizlemesi hazırlanamadı.",
    "Play": "Oynat",
    "Pause": "Duraklat",
    "Play again": "Tekrar oynat",
    "Stop": "Durdur",
    "OK": "Tamam",
    "Cancel": "Vazgeç",
    "Image": "Görsel",
    "Audio": "Ses",
    "Video": "Video",
    "Document": "Belge",
    "Table / Data": "Tablo / Veri",
    "Archive": "Arşiv",
    "Unknown": "Bilinmiyor",
    "This image could not be opened or its format is unsupported.": "Bu görsel açılamadı veya biçimi desteklenmiyor.",
    "This file format was not recognized.": "Bu dosya formatı tanınamadı.",
    "No converter is available for this format.": "Bu format için dönüştürücü yok.",
    "The required conversion engine is missing.": "Gerekli dönüştürme motoru kurulu değil.",
    "This file cannot be converted to the selected format.": "Bu dosya seçilen hedefe dönüştürülemiyor.",
    "The conversion engine did not create an output file.": "Dönüştürme motoru çıktı dosyası oluşturmadı.",
    "The output archive could not be verified.": "Çıktı arşivi doğrulanamadı.",
    "The output format could not be verified.": "Çıktı biçimi doğrulanamadı.",
    "Choose Create a copy when converting a file link.": "Bağlantı dosyaları için Kopya oluştur seçeneğini kullanın.",
    "The source file changed during conversion.": "Kaynak dosya işlem sırasında değişti.",
    "The converted file could not be found.": "Dönüştürülmüş dosya konumunda bulunamadı.",
    "A reader is unavailable for this document format.": "Bu belge biçimi için okuyucu yok.",
    "Reading Parquet requires PyArrow or fastparquet.": "Parquet okumak için PyArrow veya fastparquet gerekli.",
    "Reading this format requires {module}.": "Bu biçimi okumak için {module} bileşeni gerekli.",
    "Reading this archive requires {module}.": "Bu arşivi okumak için {module} bileşeni gerekli.",
    "Could not open the {format} archive.": "Açılamayan arşiv: {format}",
    "The archive contains an unsafe file path.": "Arşivde güvenli olmayan bir dosya yolu var.",
    "TAR links and special files are unsupported.": "TAR arşivindeki bağlantılar ve özel dosyalar desteklenmiyor.",
    "Unsupported source format · {format}": "Desteklenmeyen kaynak: {format}",
    "Unsupported target format · {format}": "Desteklenmeyen hedef: {format}",
    "{component} is missing. Install {package}.": "{component} bulunamadı. {package} paketini kurun.",
    "WebP pixel verification failed.": "WebP piksel doğrulaması başarısız.",
    "FFmpeg was not found.": "FFmpeg bulunamadı.",
    "Could not register the File Explorer extension.": "Windows Gezgin uzantısı kaydedilemedi.",
    "Could not update the File Explorer context menu.": "Sağ tık menüsü güncellenemedi.",
    "pythonw.exe was not found.": "pythonw.exe bulunamadı.",
    "Files in this location cannot safely be recycled.": "Bu konumda güvenli geri dönüşüm desteklenmiyor.",
    "The Windows file operation failed ({code}).": "Windows dosya işlemi başarısız ({code}).",
    "Windows could not move the original file to the Recycle Bin.": (
        "Windows orijinal dosyayı Geri Dönüşüm Kutusu’na taşıyamadı."
    ),
    "Could not open the output folder.": "Çıktı klasörü açılamadı.",
}


def set_language(language: str) -> None:
    global _language
    _language = language if language in LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    return _language


class Message(str):
    """Keep an engine message translatable even after conversion finishes."""

    def __new__(cls, source: str, **values):
        text = super().__new__(cls, source.format(**values) if values else source)
        text.source = source
        text.values = values
        return text


def tr(source: str | Exception, *, language: str | None = None, **values) -> str:
    if isinstance(source, Exception):
        if len(source.args) == 1 and isinstance(source.args[0], Message):
            source = source.args[0]
        elif isinstance(source, OSError) and (code := getattr(source, "winerror", None)) is not None:
            source = Message("The Windows file operation failed ({code}).", code=f"0x{code & 0xffffffff:08X}")
        else:
            source = str(source) or type(source).__name__
    if isinstance(source, Message):
        values = source.values
        source = source.source
    selected = _language if language is None else language
    text = _TURKISH.get(source, source) if selected == "tr" else source
    values = {
        key: tr(value, language=selected) if isinstance(value, (Message, Exception)) else value
        for key, value in values.items()
    }
    return text.format(**values) if values else text
