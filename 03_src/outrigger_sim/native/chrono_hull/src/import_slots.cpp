#include "import_slots.h"

#include <bcrypt.h>

#include <array>
#include <cctype>
#include <cstddef>
#include <fstream>
#include <vector>

namespace outrigger::hull {
namespace {

bool EqualsIgnoreCase(std::string_view a, std::string_view b) {
  if (a.size() != b.size()) return false;
  for (std::size_t i = 0; i < a.size(); ++i) {
    if (std::tolower(static_cast<unsigned char>(a[i])) !=
        std::tolower(static_cast<unsigned char>(b[i]))) {
      return false;
    }
  }
  return true;
}

/// Pointer into a loaded image at a relative virtual address.
template <typename T>
T* AtRva(HMODULE module, DWORD rva) {
  // A loaded PE image is one contiguous mapping, so RVAs are byte offsets
  // from the module base.
  return reinterpret_cast<T*>(reinterpret_cast<std::byte*>(module) + rva);
}

const IMAGE_IMPORT_DESCRIPTOR* FirstImportDescriptor(HMODULE module) {
  const auto* dos = AtRva<const IMAGE_DOS_HEADER>(module, 0);
  if (dos->e_magic != IMAGE_DOS_SIGNATURE) return nullptr;
  const auto* nt = AtRva<const IMAGE_NT_HEADERS64>(module, dos->e_lfanew);
  if (nt->Signature != IMAGE_NT_SIGNATURE ||
      nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
    return nullptr;
  }
  const IMAGE_DATA_DIRECTORY& directory =
      nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
  if (directory.VirtualAddress == 0 || directory.Size == 0) return nullptr;
  return AtRva<const IMAGE_IMPORT_DESCRIPTOR>(module, directory.VirtualAddress);
}

}  // namespace

void** FindImportSlot(HMODULE importer, std::string_view exporter_dll_name,
                      std::string_view function_name) {
  for (const IMAGE_IMPORT_DESCRIPTOR* descriptor = FirstImportDescriptor(importer);
       descriptor != nullptr && descriptor->Name != 0; ++descriptor) {
    const char* dll_name = AtRva<const char>(importer, descriptor->Name);
    if (!EqualsIgnoreCase(dll_name, exporter_dll_name)) continue;
    // The name table (OriginalFirstThunk) and the address table (FirstThunk)
    // run in parallel; the latter holds the bound function pointers.
    if (descriptor->OriginalFirstThunk == 0) return nullptr;
    const auto* names = AtRva<const IMAGE_THUNK_DATA64>(importer, descriptor->OriginalFirstThunk);
    auto* addresses = AtRva<IMAGE_THUNK_DATA64>(importer, descriptor->FirstThunk);
    for (; names->u1.AddressOfData != 0; ++names, ++addresses) {
      if (IMAGE_SNAP_BY_ORDINAL64(names->u1.Ordinal)) continue;
      const auto* by_name =
          AtRva<const IMAGE_IMPORT_BY_NAME>(importer, static_cast<DWORD>(names->u1.AddressOfData));
      if (function_name == reinterpret_cast<const char*>(by_name->Name)) {
        return reinterpret_cast<void**>(&addresses->u1.Function);
      }
    }
  }
  return nullptr;
}

bool WriteImportSlot(void** slot, void* value) {
  DWORD old_protection = 0;
  if (!VirtualProtect(slot, sizeof(void*), PAGE_READWRITE, &old_protection)) {
    return false;
  }
  InterlockedExchangePointer(slot, value);
  DWORD ignored = 0;
  VirtualProtect(slot, sizeof(void*), old_protection, &ignored);
  FlushInstructionCache(GetCurrentProcess(), slot, sizeof(void*));
  return true;
}

std::optional<std::filesystem::path> ModulePath(HMODULE module) {
  std::vector<wchar_t> buffer(MAX_PATH);
  while (true) {
    const DWORD length =
        GetModuleFileNameW(module, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (length == 0) return std::nullopt;
    if (length < buffer.size()) return std::filesystem::path(buffer.data());
    buffer.resize(buffer.size() * 2);
  }
}

std::optional<std::string> FileSha256Hex(const std::filesystem::path& path) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream.is_open()) return std::nullopt;

  BCRYPT_ALG_HANDLE algorithm = nullptr;
  if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) != 0) {
    return std::nullopt;
  }
  BCRYPT_HASH_HANDLE hash = nullptr;
  std::optional<std::string> hex;
  if (BCryptCreateHash(algorithm, &hash, nullptr, 0, nullptr, 0, 0) == 0) {
    std::vector<char> chunk(1 << 20);
    bool ok = true;
    while (ok && stream) {
      stream.read(chunk.data(), static_cast<std::streamsize>(chunk.size()));
      const auto count = static_cast<ULONG>(stream.gcount());
      if (count > 0) {
        ok = BCryptHashData(hash, reinterpret_cast<PUCHAR>(chunk.data()), count, 0) == 0;
      }
    }
    std::array<UCHAR, 32> digest{};
    if (ok && BCryptFinishHash(hash, digest.data(), static_cast<ULONG>(digest.size()), 0) == 0) {
      constexpr char kHexDigits[] = "0123456789abcdef";
      hex.emplace();
      for (const UCHAR byte : digest) {
        hex->push_back(kHexDigits[byte >> 4]);
        hex->push_back(kHexDigits[byte & 0x0F]);
      }
    }
    BCryptDestroyHash(hash);
  }
  BCryptCloseAlgorithmProvider(algorithm, 0);
  return hex;
}

}  // namespace outrigger::hull
