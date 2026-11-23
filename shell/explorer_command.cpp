#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shobjidl.h>
#include <shlwapi.h>

#include <algorithm>
#include <memory>
#include <new>
#include <string>
#include <utility>
#include <vector>

namespace {
constexpr CLSID command_id = {
    0xf02a60f2, 0x41a0, 0x46ef, {0x9c, 0x45, 0x88, 0x8e, 0x05, 0x2e, 0x19, 0x4f}
};
HMODULE module;
volatile LONG live_objects = 0;

std::wstring project_directory() {
    std::wstring path(32768, L'\0');
    const DWORD length = GetModuleFileNameW(module, path.data(), static_cast<DWORD>(path.size()));
    if (length == 0 || length == path.size()) {
        return {};
    }
    path.resize(length);
    for (int depth = 0; depth < 3; ++depth) {
        const auto separator = path.find_last_of(L"\\/");
        if (separator == std::wstring::npos) {
            return {};
        }
        path.resize(separator);
    }
    return path;
}

void append_argument(std::wstring& command_line, const std::wstring& argument) {
    if (!command_line.empty()) {
        command_line += L' ';
    }
    command_line += L'"';
    size_t slashes = 0;
    for (const auto character : argument) {
        if (character == L'\\') {
            ++slashes;
            continue;
        }
        command_line.append(character == L'"' ? slashes * 2 + 1 : slashes, L'\\');
        command_line += character;
        slashes = 0;
    }
    command_line.append(slashes * 2, L'\\');
    command_line += L'"';
}


constexpr wchar_t settings_key[] = L"Software\\DosyaDonusturucu";

struct MenuEntry {
    std::wstring argument;
    std::wstring title;
    std::wstring extensions;
};

bool english() {
    wchar_t language[3] = {};
    DWORD size = sizeof(language);
    return RegGetValueW(HKEY_CURRENT_USER, settings_key, L"Language", RRF_RT_REG_SZ,
                        nullptr, language, &size) == ERROR_SUCCESS
        && lstrcmpW(language, L"en") == 0;
}

std::wstring configured_python(const std::wstring& directory) {
    std::wstring value(32768, L'\0');
    DWORD size = static_cast<DWORD>(value.size() * sizeof(wchar_t));
    if (RegGetValueW(HKEY_CURRENT_USER, settings_key, L"ExplorerPython", RRF_RT_REG_SZ,
                     nullptr, value.data(), &size) == ERROR_SUCCESS && value[0]) {
        value.resize(size / sizeof(wchar_t) - 1);
        return value;
    }
    return directory + L"\\.venv\\Scripts\\pythonw.exe";
}

std::vector<MenuEntry> menu_entries() {
    std::vector<MenuEntry> rows;
    DWORD size = 0;
    if (RegGetValueW(HKEY_CURRENT_USER, settings_key, L"ExplorerPresets", RRF_RT_REG_MULTI_SZ,
                     nullptr, nullptr, &size) == ERROR_SUCCESS && size && size < 1024 * 1024) {
        std::vector<wchar_t> storage(size / sizeof(wchar_t) + 2, L'\0');
        if (RegGetValueW(HKEY_CURRENT_USER, settings_key, L"ExplorerPresets", RRF_RT_REG_MULTI_SZ,
                         nullptr, storage.data(), &size) == ERROR_SUCCESS) {
            for (auto* start = storage.data(); *start;) {
                const std::wstring row(start);
                start += row.size() + 1;
                const auto first = row.find(L'\t');
                if (first == std::wstring::npos) {
                    continue;
                }
                const auto second = row.find(L'\t', first + 1);
                if (second != std::wstring::npos && first && second + 1 < row.size()) {
                    rows.push_back({row.substr(0, first), row.substr(second + 1),
                                    L"," + row.substr(first + 1, second - first - 1) + L","});
                }
            }
        }
    }
    rows.push_back({L"", english() ? L"Open DeskConvert" : L"DeskConvert\u2019i a\u00E7", L""});
    rows.push_back({L"--configure-presets",
                    english() ? L"Manage presets" : L"Haz\u0131r ayarlar\u0131 d\u00FCzenle", L""});
    return rows;
}

struct TaskMemory {
    void operator()(wchar_t* pointer) const { CoTaskMemFree(pointer); }
};

std::unique_ptr<wchar_t, TaskMemory> selected_path(IShellItemArray* selection, DWORD index) {
    IShellItem* item = nullptr;
    if (FAILED(selection->GetItemAt(index, &item))) {
        return {};
    }
    PWSTR path = nullptr;
    const auto result = item->GetDisplayName(SIGDN_FILESYSPATH, &path);
    item->Release();
    if (FAILED(result)) {
        CoTaskMemFree(path);
        return {};
    }
    return std::unique_ptr<wchar_t, TaskMemory>(path);
}

class CommandEnumerator;

class ExplorerCommand final : public IExplorerCommand {
    volatile LONG references_ = 1;
    MenuEntry entry_;
    bool parent_;

public:
    ExplorerCommand() : parent_(true) { InterlockedIncrement(&live_objects); }
    explicit ExplorerCommand(MenuEntry entry) : entry_(std::move(entry)), parent_(false) {
        InterlockedIncrement(&live_objects);
    }
    ~ExplorerCommand() { InterlockedDecrement(&live_objects); }

    STDMETHODIMP QueryInterface(REFIID iid, void** object) override {
        *object = nullptr;
        if (!IsEqualIID(iid, IID_IUnknown) && !IsEqualIID(iid, __uuidof(IExplorerCommand))) {
            return E_NOINTERFACE;
        }
        *object = static_cast<IExplorerCommand*>(this);
        AddRef();
        return S_OK;
    }

    STDMETHODIMP_(ULONG) AddRef() override { return InterlockedIncrement(&references_); }
    STDMETHODIMP_(ULONG) Release() override {
        const auto remaining = InterlockedDecrement(&references_);
        if (remaining == 0) {
            delete this;
        }
        return remaining;
    }

    STDMETHODIMP GetTitle(IShellItemArray*, LPWSTR* title) override {
        return SHStrDupW(parent_ ? L"DeskConvert" : entry_.title.c_str(), title);
    }

    STDMETHODIMP GetIcon(IShellItemArray*, LPWSTR* icon) override {
        try {
            const auto path = project_directory() + L"\\assets\\icon.ico";
            return SHStrDupW(path.c_str(), icon);
        } catch (...) {
            return E_OUTOFMEMORY;
        }
    }

    STDMETHODIMP GetToolTip(IShellItemArray*, LPWSTR* tip) override {
        *tip = nullptr;
        return E_NOTIMPL;
    }

    STDMETHODIMP GetCanonicalName(GUID* name) override {

        *name = command_id;
        if (!parent_) {
            DWORD hash = 2166136261u;
            for (const auto character : entry_.argument) {
                hash = (hash ^ character) * 16777619u;
            }
            name->Data1 ^= hash;
        }
        return S_OK;
    }

    STDMETHODIMP GetState(IShellItemArray* selection, BOOL, EXPCMDSTATE* state) override {
        DWORD count = 0;
        if (selection) {
            selection->GetCount(&count);
        }
        *state = count > 0 ? ECS_ENABLED : ECS_HIDDEN;
        if (entry_.extensions.empty()) {
            return S_OK;
        }
        try {
            for (DWORD index = 0; index < count; ++index) {
                const auto path = selected_path(selection, index);
                if (!path) {
                    *state = ECS_HIDDEN;
                    break;
                }
                const auto suffix = PathFindExtensionW(path.get());
                if (*suffix != L'.') {
                    *state = ECS_HIDDEN;
                    break;
                }
                std::wstring extension(suffix + 1);
                if (!extension.empty()) {
                    CharLowerBuffW(extension.data(), static_cast<DWORD>(extension.size()));
                }
                if (entry_.extensions.find(L"," + extension + L",") == std::wstring::npos) {
                    *state = ECS_HIDDEN;
                    break;
                }
            }
        } catch (...) {
            return E_OUTOFMEMORY;
        }
        return S_OK;
    }

    STDMETHODIMP GetFlags(EXPCMDFLAGS* flags) override {
        *flags = parent_ ? ECF_HASSUBCOMMANDS : ECF_DEFAULT;
        return S_OK;
    }

    STDMETHODIMP EnumSubCommands(IEnumExplorerCommand** commands) override;

    STDMETHODIMP Invoke(IShellItemArray* selection, IBindCtx*) override {
        if (!selection || parent_) {
            return E_INVALIDARG;
        }
        try {
            return launch(selection);
        } catch (...) {
            return E_OUTOFMEMORY;
        }
    }

private:
    HRESULT launch(IShellItemArray* selection) {
        DWORD count = 0;
        HRESULT result = selection->GetCount(&count);
        if (FAILED(result) || count == 0) {
            return FAILED(result) ? result : E_INVALIDARG;
        }
        const auto directory = project_directory();
        if (directory.empty()) {
            return E_FAIL;
        }

        const auto executable = configured_python(directory);
        std::wstring command_line;
        append_argument(command_line, executable);
        append_argument(command_line, directory + L"\\app.py");
        if (entry_.argument == L"--configure-presets") {
            append_argument(command_line, entry_.argument);
        } else {
            if (!entry_.argument.empty()) {
                append_argument(command_line, L"--preset");
                append_argument(command_line, entry_.argument);
            }
            append_argument(command_line, L"--");
            const auto prefix_length = command_line.size();
            for (DWORD index = 0; index < count; ++index) {
                const auto path = selected_path(selection, index);
                if (path) {
                    append_argument(command_line, path.get());
                }
            }
            if (prefix_length == command_line.size()) {
                return HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND);
            }
        }
        if (command_line.size() + 1 >= 32767) {
            return HRESULT_FROM_WIN32(ERROR_FILENAME_EXCED_RANGE);
        }
        STARTUPINFOW startup{};
        startup.cb = sizeof(startup);
        PROCESS_INFORMATION process{};
        if (!CreateProcessW(executable.c_str(), command_line.data(), nullptr, nullptr, FALSE,
                            0, nullptr, directory.c_str(), &startup, &process)) {
            return HRESULT_FROM_WIN32(GetLastError());
        }
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
        return S_OK;
    }
};


class CommandEnumerator final : public IEnumExplorerCommand {
    volatile LONG references_ = 1;
    std::vector<MenuEntry> entries_;
    size_t position_;

public:
    explicit CommandEnumerator(std::vector<MenuEntry> entries, size_t position = 0)
        : entries_(std::move(entries)), position_(position) { InterlockedIncrement(&live_objects); }
    ~CommandEnumerator() { InterlockedDecrement(&live_objects); }

    STDMETHODIMP QueryInterface(REFIID iid, void** object) override {
        *object = nullptr;
        if (!IsEqualIID(iid, IID_IUnknown) && !IsEqualIID(iid, __uuidof(IEnumExplorerCommand))) {
            return E_NOINTERFACE;
        }
        *object = static_cast<IEnumExplorerCommand*>(this);
        AddRef();
        return S_OK;
    }
    STDMETHODIMP_(ULONG) AddRef() override { return InterlockedIncrement(&references_); }
    STDMETHODIMP_(ULONG) Release() override {
        const auto remaining = InterlockedDecrement(&references_);
        if (!remaining) {
            delete this;
        }
        return remaining;
    }

    STDMETHODIMP Next(ULONG count, IExplorerCommand** commands, ULONG* fetched) override {
        if (!commands || (!fetched && count != 1)) {
            return E_POINTER;
        }
        ULONG done = 0;
        const auto original = position_;
        try {
            while (done < count && position_ < entries_.size()) {
                commands[done] = new ExplorerCommand(entries_[position_]);
                ++done;
                ++position_;
            }
        } catch (...) {
            while (done) {
                commands[--done]->Release();
                commands[done] = nullptr;
            }
            position_ = original;
            if (fetched) {
                *fetched = 0;
            }
            return E_OUTOFMEMORY;
        }
        if (fetched) {
            *fetched = done;
        }
        return done == count ? S_OK : S_FALSE;
    }

    STDMETHODIMP Skip(ULONG count) override {
        const auto skipped = std::min<size_t>(count, entries_.size() - position_);
        position_ += skipped;
        return skipped == count ? S_OK : S_FALSE;
    }

    STDMETHODIMP Reset() override { position_ = 0; return S_OK; }

    STDMETHODIMP Clone(IEnumExplorerCommand** copy) override {
        if (!copy) {
            return E_POINTER;
        }
        *copy = nullptr;
        try {
            *copy = new CommandEnumerator(entries_, position_);
            return S_OK;
        } catch (...) {
            return E_OUTOFMEMORY;
        }
    }
};

STDMETHODIMP ExplorerCommand::EnumSubCommands(IEnumExplorerCommand** commands) {
    if (!commands) {
        return E_POINTER;
    }
    *commands = nullptr;
    if (!parent_) {
        return E_NOTIMPL;
    }
    try {
        *commands = new CommandEnumerator(menu_entries());
        return S_OK;
    } catch (...) {
        return E_OUTOFMEMORY;
    }
}

class CommandFactory final : public IClassFactory {
    volatile LONG references_ = 1;

public:
    CommandFactory() { InterlockedIncrement(&live_objects); }
    ~CommandFactory() { InterlockedDecrement(&live_objects); }

    STDMETHODIMP QueryInterface(REFIID iid, void** object) override {
        *object = nullptr;
        if (!IsEqualIID(iid, IID_IUnknown) && !IsEqualIID(iid, IID_IClassFactory)) {
            return E_NOINTERFACE;
        }
        *object = static_cast<IClassFactory*>(this);
        AddRef();
        return S_OK;
    }

    STDMETHODIMP_(ULONG) AddRef() override { return InterlockedIncrement(&references_); }
    STDMETHODIMP_(ULONG) Release() override {
        const auto remaining = InterlockedDecrement(&references_);
        if (remaining == 0) {
            delete this;
        }
        return remaining;
    }

    STDMETHODIMP CreateInstance(IUnknown* outer, REFIID iid, void** object) override {
        *object = nullptr;
        if (outer) {
            return CLASS_E_NOAGGREGATION;
        }
        auto* command = new (std::nothrow) ExplorerCommand();
        if (!command) {
            return E_OUTOFMEMORY;
        }
        const HRESULT result = command->QueryInterface(iid, object);
        command->Release();
        return result;
    }

    STDMETHODIMP LockServer(BOOL lock) override {
        if (lock) {
            InterlockedIncrement(&live_objects);
        } else {
            InterlockedDecrement(&live_objects);
        }
        return S_OK;
    }
};
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        module = instance;
    }
    return TRUE;
}

STDAPI DllGetClassObject(REFCLSID id, REFIID iid, void** object) {
    *object = nullptr;
    if (!IsEqualCLSID(id, command_id)) {
        return CLASS_E_CLASSNOTAVAILABLE;
    }
    auto* factory = new (std::nothrow) CommandFactory();
    if (!factory) {
        return E_OUTOFMEMORY;
    }
    const HRESULT result = factory->QueryInterface(iid, object);
    factory->Release();
    return result;
}

STDAPI DllCanUnloadNow() {
    return InterlockedCompareExchange(&live_objects, 0, 0) == 0 ? S_OK : S_FALSE;
}
