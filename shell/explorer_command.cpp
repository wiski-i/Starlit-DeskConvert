#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shobjidl.h>
#include <shlwapi.h>

#include <new>
#include <string>

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

class ExplorerCommand final : public IExplorerCommand {
    volatile LONG references_ = 1;

public:
    ExplorerCommand() { InterlockedIncrement(&live_objects); }
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
        wchar_t language[3] = {};
        DWORD size = sizeof(language);
        const auto result = RegGetValueW(
            HKEY_CURRENT_USER, L"Software\\DosyaDonusturucu", L"Language",
            RRF_RT_REG_SZ, nullptr, language, &size
        );
        const bool english = result == ERROR_SUCCESS && lstrcmpW(language, L"en") == 0;
        return SHStrDupW(english ? L"Convert File" : L"Dosya D\u00F6n\u00FC\u015Ft\u00FCr", title);
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
        return S_OK;
    }

    STDMETHODIMP GetState(IShellItemArray* selection, BOOL, EXPCMDSTATE* state) override {
        DWORD count = 0;
        if (selection) {
            selection->GetCount(&count);
        }
        *state = count > 0 ? ECS_ENABLED : ECS_HIDDEN;
        return S_OK;
    }

    STDMETHODIMP GetFlags(EXPCMDFLAGS* flags) override {
        *flags = ECF_DEFAULT;
        return S_OK;
    }

    STDMETHODIMP EnumSubCommands(IEnumExplorerCommand** commands) override {
        *commands = nullptr;
        return E_NOTIMPL;
    }

    STDMETHODIMP Invoke(IShellItemArray* selection, IBindCtx*) override {
        if (!selection) {
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
        const auto executable = directory + L"\\.venv\\Scripts\\pythonw.exe";
        std::wstring command_line;
        append_argument(command_line, executable);
        append_argument(command_line, directory + L"\\app.py");
        append_argument(command_line, L"--");
        const auto prefix_length = command_line.size();
        for (DWORD index = 0; index < count; ++index) {
            IShellItem* item = nullptr;
            if (FAILED(selection->GetItemAt(index, &item))) {
                continue;
            }
            PWSTR path = nullptr;
            result = item->GetDisplayName(SIGDN_FILESYSPATH, &path);
            item->Release();
            if (SUCCEEDED(result)) {
                try {
                    append_argument(command_line, path);
                } catch (...) {
                    CoTaskMemFree(path);
                    throw;
                }
                CoTaskMemFree(path);
            }
        }
        if (prefix_length == command_line.size()) {
            return HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND);
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

extern "C" __declspec(dllexport) HRESULT WINAPI DllGetClassObject(REFCLSID id, REFIID iid, void** object) {
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

extern "C" __declspec(dllexport) HRESULT WINAPI DllCanUnloadNow() {
    return InterlockedCompareExchange(&live_objects, 0, 0) == 0 ? S_OK : S_FALSE;
}
