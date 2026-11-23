# DeskConvert

Convert images, video, audio, documents, tables, and archives on your Windows PC.

## Start the app

Install Python 3.10 or later and make it available as `python`. Double-click
`Başlat.bat` to install dependencies and launch the app. Initial installation
needs internet access. The installed conversion engines run locally.

To launch from PowerShell after installation, run:

```powershell
.venv\Scripts\python.exe app.py
```

## Convert from File Explorer

1. In the app, select **Sağ tık menüsüne ekle** / **Add to context menu**.
2. Right-click a supported file and open **DeskConvert**. On Windows 11, the
   signed extension can appear in the main menu. The classic menu is under
   **Show more options** and groups scale, rotation, and tempo presets.
3. Select a preset to start conversion immediately. **Open DeskConvert** adds
   the selection to the queue without starting a conversion.
4. Use **Manage presets** in Explorer or in the app to add, edit, duplicate,
   disable, reorder, or remove presets.

The Windows 11 extension takes the selection as a single batch and shows
presets compatible with every selected extension. The classic menu takes one
file. Multiple files can also be dragged into the app or selected in the file
picker. Formats are verified again when the conversion starts.

The menu is registered for the current account. Use the menu toggle to remove
it. If you move the project or its Python environment, remove and re-add it.

## Presets and formats

- **Video** — MP4, MKV, AVI, WebM, OGV, and GIF. Presets include smaller
  MP4/GIF files, 75% and 25% scale, 720p and 1080p height limits, left and
  right rotation, and H.264 hardware encoders where FFmpeg and the GPU support
  them. Each scale limit preserves the aspect ratio and avoids upscaling.
- **Audio** — AAC, FLAC, MP3, Ogg, and WAV, including extraction from a video.
  Set tempo, pitch, channels, bitrate, sample rate, and WAV/MP3 encoding mode.
  DVD presets work on VOB files. Audio CD presets read the track from a CDA
  file on its original Windows optical drive.
- **Images** — PNG, JPEG, ICO, WebP, AVIF, and PDF. Added inputs include camera
  RAW, DDS, EXR, PSD, XCF, and SVG. Image presets support scaling, rotation,
  quality, and sizes rounded down to powers of two.
- **Documents** — PDF to separate image files, one per page. Word, Excel, and
  PowerPoint inputs use their installed Microsoft Office application for PDF
  or page-image export. Existing document, table, and archive routes are
  available in the regular format picker.

Presets can filter input extensions and set an output path. Common tokens
include **(p)** for the source or selected folder, **(f)** for the original
basename, **(i)** and **(o)** for extensions, **(n:i)** and **(n:c)** for page
numbers and counts, and **(p:d)**, **(p:m)**, **(p:v)** and **(p:p)** for
Windows' Documents, Music, Videos, and Pictures folders. **(d0)** names the
source's parent folder, **(d1)** the folder above it, and **(d:yyyy-MM-dd)**
formats the date. Example: **(p)Converted/(f)**.

Source actions can keep the original, move it to **Conversion Archives**,
recycle it, or delete it. Recycle and permanent deletion require confirmation,
and source actions run after successful output verification. Preset settings
also allow a limited set of advanced FFmpeg output and filter options,
simultaneous conversions, and copying the completed files to the clipboard.
A Git checkout can also opt into a GitHub update check. The check uses local
Git or GitHub CLI authentication and leaves updating the checkout to the user.

## Change the interface language

Choose **Türkçe** or **English** at the top of the window. DeskConvert saves
your choice for the next launch and uses it for the File Explorer command.
The Windows file and folder pickers use your Windows display language.

## Preview a file

Click the preview or select **Büyüt**. Press **F3** to open it from the
keyboard and **Esc** to close it. The preview can display images, play
animated images, show up to 60 seconds of video without sound, play up to
45 seconds of audio, and show text, table samples, or archive listings.
Windows' animation-effects preference controls the preview transition.

## Save the result

- **Kopya oluştur** keeps the source. Choose a destination folder or use the
  source folder.
- **Orijinalin yerine koy** writes the converted file beside the source and
  checks that the output is readable. It then asks Windows to recycle the
  original. If recycling fails, the app keeps both files and reports the warning.

If a destination filename already exists, the app saves a new numbered file.

Select a completed file in the queue and choose **Show output** to highlight
its output in File Explorer. Select a failed file and choose **Show error**
to read the full message.

In a batch, choose **Stop after active files** to finish in-progress files before
stopping. **Clear completed** removes successful items from the queue so you
can continue with the remaining items. It leaves output files on disk.

## Conversion details

- Static PNG files with up to 8 bits per channel can be converted to WebP with
  verified pixel and transparency preservation. WebP conversion refuses
  animated PNG and 16-bit PNG. Some image metadata is format-specific.
- Video to GIF uses a generated color palette, removes audio, uses 12 frames
  per second, and limits the width to 480 pixels without upscaling.
- Compatible video streams can be copied into a different container without
  re-encoding. Other video conversions use the target encoder.
- Document conversion limits access to the chosen source file. External
  resources referenced by the document may be omitted from the result.
- Plain text accepts UTF-8, UTF-16 with a byte order mark, and Windows-1254.
- Optional readers are required for legacy Excel, ODS, YAML, and Parquet.
  The format picker hides targets that need a missing dependency.
- TAR extraction supports regular files and directories. RAR reading
  requires a compatible optional backend.

## Run checks

```powershell
.venv\Scripts\python.exe -m unittest test_presets test_conversion_safety
```

```powershell
.venv\Scripts\python.exe -X utf8 selftest.py
```

## Build the Windows 11 Explorer extension

The current extension target is Windows 11 x64. Use Zig 0.15.2 and
MakeAppx from the Windows SDK, or run the build with -Msvc from a Visual Studio
x64 Developer PowerShell.

```powershell
.\shell\build.ps1 -Zig C:\Tools\zig.exe -MakeAppx C:\Tools\makeappx.exe
```

The script produces the native command and an identity package in
`shell\dist`. Sign that package before registering it. For local
development, `shell\register.ps1 -SignTool C:\Tools\signtool.exe` signs the
package and exports its public certificate to `shell\dist\ExplorerMenu.cer`.
Windows may require a development certificate in the computer's Trusted
People store. Run `shell\register.ps1` after Windows trusts the signing
certificate. It registers the package for the current account using the
existing app directory as the external location.

## License

DeskConvert is licensed under the GNU General Public License, version 3
only (`GPL-3.0-only`). See [LICENSE](LICENSE) for the full text.
