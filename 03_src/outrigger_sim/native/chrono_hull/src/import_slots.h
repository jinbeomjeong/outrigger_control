// Locating and rewriting import address table (IAT) slots of a loaded module.

#pragma once

#include <windows.h>

#include <filesystem>
#include <optional>
#include <string>
#include <string_view>

namespace outrigger::hull {

/// Address of the IAT slot through which `importer` calls `function_name`
/// (an exact, decorated name) imported by name from `exporter_dll_name`
/// (compared case-insensitively). Returns nullptr if there is no such import.
/// Only regular (non-delay-load) imports are searched.
[[nodiscard]] void** FindImportSlot(HMODULE importer, std::string_view exporter_dll_name,
                                    std::string_view function_name);

/// Atomically store `value` into an IAT slot, temporarily making its page
/// writable. Returns false if the page protection could not be changed.
[[nodiscard]] bool WriteImportSlot(void** slot, void* value);

/// Full path of a loaded module, or nullopt.
[[nodiscard]] std::optional<std::filesystem::path> ModulePath(HMODULE module);

/// Lowercase hex SHA-256 of a file, or nullopt if it cannot be read.
[[nodiscard]] std::optional<std::string> FileSha256Hex(const std::filesystem::path& path);

}  // namespace outrigger::hull
