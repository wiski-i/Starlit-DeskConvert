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

1. In the app, select **Sağ tık menüsüne ekle**.
2. Right-click a file. A registered Windows 11 extension shows the command in
   the main menu. The classic registration appears under **Show more options**.
3. Choose **Dosya Dönüştür** in Turkish or **Convert File** in English.
   DeskConvert opens with that file selected.
4. Choose the target format and a save method, then select **Dönüştür**.

The Windows 11 extension accepts multiple files. The classic command takes
one file. You can also drag several files into the app or use **Dosya Seç**.
Select a queue row to change the preview and target list. The app detects
the source and displays compatible routes for the installed engines.

The menu entry is registered for the current Windows account. Select
**Sağ tık menüsü açık** to remove it. If you move the project or its Python
environment, remove and re-add the command.

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

In a batch, choose **Stop after this file** to finish the current file before
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
.venv\Scripts\python.exe -m unittest test_conversion_safety
```

```powershell
.venv\Scripts\python.exe -X utf8 selftest.py
```

## Build the Windows 11 Explorer extension

The current extension target is Windows 11 x64. Use Zig 0.15.2 and
MakeAppx from the Windows SDK.

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
