def load_plugins(mod_names):
    import sys
    import os
    import settings

    orig_path = sys.path
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    orig_installed_plugins = settings.INSTALLED_STORAGE_PLUGINS
    settings.INSTALLED_STORAGE_PLUGINS = mod_names

    try:
        from chroma_core.lib.storage_plugin.manager import StoragePluginManager

        return StoragePluginManager()
    finally:
        sys.path = orig_path
        settings.INSTALLED_STORAGE_PLUGINS = orig_installed_plugins
