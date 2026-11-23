"""English and Turkish strings for DeskConvert."""

from __future__ import annotations

LANGUAGES = {"tr": "Türkçe", "en": "English"}
DEFAULT_LANGUAGE = "tr"
_language = DEFAULT_LANGUAGE

_TURKISH = {
    "Loading files…": "Dosyalar yükleniyor…",
    "Could not read {name}. {reason}": "{name} okunamadı. {reason}",
    "Check GitHub updates at startup": "Açılışta GitHub güncellemelerini kontrol et",
    "A newer GitHub revision is available.": "GitHub’da daha yeni bir sürüm var.",
    "Simultaneous conversions": "Eşzamanlı dönüşüm",
    "Copy converted files to clipboard": "Dönüşen dosyaları panoya kopyala",
    "Stop after active files": "Süren işlemlerden sonra dur",
    "Finishing active files before stopping.": "Durdurmadan önce süren işlemler tamamlanıyor.",
    'Audio channels (0 = source)': 'Ses kanalı (0 = kaynak)',
    'Sample rate (Hz)': 'Örnekleme hızı (Hz)',
    'Audio bitrate (kbps)': 'Ses bit hızı (kbps)',
    'Audio encoding': 'Ses kodlaması',
    'Advanced FFmpeg options': 'Gelişmiş FFmpeg seçenekleri',
    'Include sound': 'Sesi dahil et',
    'Power-of-two image size': 'Görsel boyutunu ikinin kuvvetine indir',
    'DVD extraction': 'DVD’den aktar',
    'Audio CD extraction': 'Ses CD’sinden aktar',
    'Document pages': 'Belge sayfaları',
    'PNG · Numbered pages': 'PNG · Numaralı sayfalar',
    'MP3 · Pitch −1 semitone': 'MP3 · Perde −1 yarım ses',
    'MP3 · Pitch +1 semitone': 'MP3 · Perde +1 yarım ses',
    'Pitch −1 semitone': 'Perde −1 yarım ses',
    'Pitch +1 semitone': 'Perde +1 yarım ses',
    'Manage presets': 'Hazır ayarları düzenle',
    'Presets': 'Hazır ayarlar',
    'New': 'Yeni',
    'Duplicate': 'Çoğalt',
    'Remove': 'Sil',
    'Move up': 'Yukarı',
    'Move down': 'Aşağı',
    'Save': 'Kaydet',
    'Restore defaults': 'Varsayılana dön',
    'Name': 'Ad',
    'Menu group': 'Menü grubu',
    'Output format': 'Çıktı biçimi',
    'Input extensions': 'Girdi uzantıları',
    'Video quality (1–100)': 'Video kalitesi (1–100)',
    'Audio quality (1–100)': 'Ses kalitesi (1–100)',
    'Image quality (1–100)': 'Görsel kalitesi (1–100)',
    'Encoding speed': 'Kodlama hızı',
    'Scale (%)': 'Ölçek (%)',
    'Height limit (px)': 'Yükseklik sınırı (px)',
    'Width limit (px)': 'Genişlik sınırı (px)',
    'Rotation (°)': 'Döndürme (°)',
    'Tempo (×)': 'Tempo (×)',
    'Pitch (semitones)': 'Perde (yarım ses)',
    'Frame rate (fps)': 'Kare hızı (fps)',
    'H.264 encoder': 'H.264 kodlayıcı',
    'Output path template': 'Çıktı yolu şablonu',
    'After conversion': 'Dönüşümden sonra',
    'Enabled': 'Etkin',
    'Blank quality uses the encoder default. Zero leaves size and frame rate unchanged. Example path template: (p)Converted/(f)': 'Kalite boşsa kodlayıcı varsayılanı kullanılır. Sıfır, boyutu ve kare hızını değiştirmez. Örnek yol: (p)Dönüşen/(f)',
    'Replace the current preset list with the defaults?': 'Şu anki listeyi varsayılan hazır ayarlarla değiştireyim mi?',
    '{name} (copy)': '{name} (kopya)',
    'New preset': 'Yeni hazır ayar',
    'Preset · {name}': 'Hazır ayar · {name}',
    'Scale to 75%': '%75’e ölçekle',
    'Scale to 25%': '%25’e ölçekle',
    'Resize to 720p': '720p’ye sığdır',
    'Resize to 1080p': '1080p’ye sığdır',
    'Rotate left': 'Sola döndür',
    'Rotate right': 'Sağa döndür',
    'Keep format': 'Biçimi koru',
    'Tempo and pitch': 'Tempo ve perde',
    'Pitch −3 semitones': 'Perdeyi 3 yarım ses düşür',
    'Pitch +3 semitones': 'Perdeyi 3 yarım ses yükselt',
    'MP4 · Small file': 'MP4 · Düşük kalite',
    'GIF · Small file': 'GIF · Düşük kalite',
    'Open DeskConvert': 'DeskConvert’i aç',
    'Could not read the preset file. {reason}': 'Hazır ayar dosyası okunamadı. {reason}',
    'This preset is missing or disabled.': 'Hazır ayar yok veya kapalı.',
    'Some selected files cannot use this preset.': 'Seçilen dosyalardan bazıları bu hazır ayarla uyumlu değil.',
    'Source action: archive': 'Kaynağı arşivle',
    'Source action: recycle': 'Kaynağı Geri Dönüşüm Kutusu’na taşı',
    'Source action: delete': 'Kaynağı kalıcı olarak sil',
    'Permanently delete originals': 'Orijinalleri kalıcı olarak sil',
    'Permanently delete {count} original file(s) after verifying the outputs?': 'Çıktılar doğrulandıktan sonra {count} orijinal dosya kalıcı olarak silinsin mi?',
    'This conversion requires Microsoft {program}.': 'Bu dönüşüm için Microsoft {program} gerekli.',
    'CDA conversion requires a Windows optical drive.': 'CDA dönüşümü için Windows’ta optik sürücü gerekli.',
    'Open the CDA track directly from the inserted audio CD.': 'CDA parçasını takılı ses CD’sinden doğrudan açın.',
    'The audio CD track could not be found.': 'Ses CD’si parçası bulunamadı.',
    'The optical drive returned an incomplete audio sector.': 'Optik sürücü eksik bir ses sektörü döndürdü.',
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
