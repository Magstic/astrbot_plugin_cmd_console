import threading
from typing import List, Dict, Optional

from pydantic import BaseModel

from astrbot.core.star.star_handler import (
    StarHandlerMetadata as StarHandler,
    star_handlers_registry,
)
from astrbot.core import sp, logger
from astrbot.core.star.star import star_map

# 1. 切换为 threading.Lock，确保在多线程环境中的原子性
shared_data_lock = threading.Lock()


# 2. 定义正确的数据模型
class CommandInfo(BaseModel):
    """代表单个指令的详细信息"""

    handler_full_name: str
    plugin_name: str
    command: str
    description: Optional[str] = "无描述"
    activated: bool


class ToggleItem(BaseModel):
    """代表前端切换指令状态时发送的数据"""

    handler_full_name: str


# 3. 全局变量
disabled_handler_cache: Dict[str, StarHandler] = {}
INACTIVATED_COMMANDS_KEY = "inactivated_command_handlers"


def initialize_disabled_commands():
    """从持久化存储中加载已禁用的指令，并更新当前注册表"""
    with shared_data_lock:
        inactivated_list = sp.get(INACTIVATED_COMMANDS_KEY, [])
        if not inactivated_list:
            return

        # 使用 list() 创建副本以安全地迭代和修改
        handlers_to_disable = [
            h
            for h in list(star_handlers_registry)
            if h.handler_full_name in inactivated_list
        ]

        for handler in handlers_to_disable:
            star_handlers_registry.remove(handler)
            disabled_handler_cache[handler.handler_full_name] = handler

        if handlers_to_disable:
            logger.info(f"成功恢复 {len(handlers_to_disable)} 个已禁用的指令状态。")


# 5. 核心逻辑函数 (线程安全且逻辑正确)
def get_all_commands() -> List[CommandInfo]:
    """获取所有已注册的指令信息，包括已禁用的（线程安全）"""
    from astrbot.core.star.filter.command import CommandFilter
    from astrbot.core.star.filter.command_group import CommandGroupFilter

    with shared_data_lock:
        all_commands_map: Dict[str, CommandInfo] = {}

        all_handlers = list(star_handlers_registry) + list(
            disabled_handler_cache.values()
        )

        for handler in all_handlers:
            is_activated = handler.handler_full_name not in disabled_handler_cache

            command_filters = [
                f
                for f in handler.event_filters
                if isinstance(f, (CommandFilter, CommandGroupFilter))
            ]
            if not command_filters:
                continue

            command_parts = []
            for f in command_filters:
                if isinstance(f, CommandGroupFilter):
                    # CommandGroupFilter has a helper to get all names
                    all_names = f.get_complete_command_names()
                    command_parts.extend(all_names)
                elif isinstance(f, CommandFilter):
                    # CommandFilter does NOT, so we build them manually
                    all_names = []
                    base_names = [f.command_name] + list(f.alias)
                    for parent in f.parent_command_names:
                        for base in base_names:
                            if parent:
                                all_names.append(f"{parent.strip()} {base.strip()}")
                            else:
                                all_names.append(base.strip())
                    command_parts.extend(all_names)

            command_str = ", ".join(sorted(list(set(command_parts))))

            if not command_str:
                continue

            plugin_metadata = star_map.get(handler.handler_module_path)
            plugin_name = plugin_metadata.name if plugin_metadata else "未知插件"

            all_commands_map[handler.handler_full_name] = CommandInfo(
                handler_full_name=handler.handler_full_name,
                plugin_name=plugin_name,
                command=command_str,
                description=handler.desc.strip() or "无描述",
                activated=is_activated,
            )

        final_list = list(all_commands_map.values())
        final_list.sort(key=lambda x: (x.plugin_name, x.command))
        return final_list


def toggle_command(item: ToggleItem):
    """启用或禁用一个指令（线程安全）"""
    with shared_data_lock:
        handler_full_name = item.handler_full_name

        # Case 1: Command is currently activated, we need to disable it.
        found_handler = next(
            (
                h
                for h in star_handlers_registry
                if h.handler_full_name == handler_full_name
            ),
            None,
        )
        if found_handler:
            star_handlers_registry.remove(found_handler)
            disabled_handler_cache[handler_full_name] = found_handler
            logger.info(f"指令 '{handler_full_name}' 已被禁用。")

        # Case 2: Command is currently disabled, we need to enable it.
        elif handler_full_name in disabled_handler_cache:
            handler_to_reactivate = disabled_handler_cache.pop(handler_full_name)
            star_handlers_registry.append(handler_to_reactivate)
            logger.info(f"指令 '{handler_full_name}' 已被重新启用。")

        else:
            logger.warning(f"尝试切换一个不存在或无法识别的指令: {handler_full_name}")
            return {"status": "error", "message": "指令不存在或无法识别"}

        # Persist changes
        inactivated_list = list(disabled_handler_cache.keys())
        sp.put(INACTIVATED_COMMANDS_KEY, inactivated_list)

        return {"status": "ok"}
