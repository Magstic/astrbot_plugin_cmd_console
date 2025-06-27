# 指令控制台 (Command Console)

Powered by Claude 4s & Gemini 2.5 Pro, All.

---

為 AstrBot 設計的 WebUI 指令管理面板。

允許 Admin 實時啟用或禁用其他插件的指令，而無需重啟機器人。

** 请注意：禁用插件并不会释放禁用的指令，唯有在禁用插件後重载 Astrbot 才可释放。**

WebUI 的安全验证设计灵感来自 [Meme Manager](https://github.com/anka-afk/astrbot_plugin_meme_manager)。

我不会去维护它，因为它即将被官方的指令支持所淘汰 : ) Readme 亦然，它们均为 AI 生成。

## ✨ 功能特性

- **WebUI 面板**: 通過網頁界面，集中查看所有已註冊的插件指令。
- **實時控制**: 一鍵啟用或禁用任何指令，變更立即生效。
- **狀態持久化**: 禁用狀態會被自動保存，即使 AstrBot 重啟，配置也不會丟失。
- **安全訪問**: WebUI 設有安全驗證，只有管理員才能訪問和操作。
- **輕量高效**: 採用 FastAPI 和獨立線程運行，對主程序性能影響極小。

## 🚀 安裝與依賴

1.  將 `astrbot_plugin_command_manager` 文件夾放入 AstrBot 的 `plugins` 目錄下。
2.  安裝所需的依賴包：
    ```bash
    pip install -r requirements.txt
    ```

## 🛠️ 使用說明

### 指令列表

- `/cmdmgr on` (別名: `/指令管理 on`)
  - **權限**: 管理員
  - **功能**: 啟動 WebUI 管理控制台。成功後，Bot 將私訊返回 **一次性** Token 義工登入。

- `/cmdmgr off` (別名: `/指令管理 off`)
  - **權限**: 管理員
  - **功能**: 關閉正在運行的 WebUI 管理控制台，釋放網路端口。

### WebUI 操作流程

1.  對機器人發送 `/cmdmgr on` 指令。
2.  獲取訪問 Token。
3.  在瀏覽器中打開 http://[主機]:[5000]/，輸入獲取的 Token 進行登錄。
4.  登錄成功後，你將看到一個包含所有指令的列表，上面清晰地標明了指令名稱、所屬插件以及當前的激活狀態。
5.  點擊每個指令旁邊的開關，即可實時啟用或禁用該指令。操作結果會立即在 AstrBot 中生效。

## ⚙️ 配置選項

本插件的 WebUI 伺服器預設配置如下：

- **端口 (Port)**: `5000`

如果需要修改端口號，請直接編輯 `main.py` 文件中的 `_start_webui` 方法。

## 🔬 技術實現簡介

本插件採用了職責分離的設計架構：

- `main.py`: 作為總控制器，負責響應管理員指令，管理 WebUI 後台的生命週期。
- `logic.py`: 插件的核心，直接操作 AstrBot 框架的內部指令註冊表 `star_handlers_registry`，通過移除和添加處理程序 (Handler) 來實現指令的動態禁用與啟用。
- `webui.py`: 基於 FastAPI 構建的 Web 後端，提供安全的 API 接口供前端頁面調用，並將靜態網頁文件呈現給用戶。

> **⚠️ 維護警告**: 本插件的核心功能與 AstrBot 框架的內部實現緊密耦合。未來若 AstrBot 框架版本更新並重構其指令註冊機制，可能會導致本插件失效。請在更新框架後注意測試兼容性。