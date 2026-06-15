def classFactory(iface):
    from .plugin import CarbonMapperPlugin
    return CarbonMapperPlugin(iface)