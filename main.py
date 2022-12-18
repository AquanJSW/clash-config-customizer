from layout import get_layout
from config import *


def main():
    # Get configuration from cmdline
    layout = get_layout()

    # Instantiate template configs
    template_configs = [
        TemplateConfig(data=data, geometry_key=layout.geometry_key)
        for data in layout.template_configs
    ]

    subscription_config_collection = SubscriptionConfigCollection(
        data=layout.subscription_configs,
        enable_renames=layout.enable_renames,
    )
    # preprocessing
    subscription_config_collection.update_ingress_IPs()
    subscription_config_collection.update_egress_IPs(layout.clash_bin)
    subscription_config_collection.log_proxies_info()
    subscription_config_collection.purify_proxies()
    # postprocessing
    subscription_config_collection.update_geometry(layout.get_geometry)
    country_map = subscription_config_collection.rename_proxies(
        layout.proxy_name_fmt_4, layout.proxy_name_fmt_6, layout.prefixes
    )

    for template_config, output_path in zip(template_configs, layout.output_paths):
        template_config.inject(country_map=country_map)
        template_config.save(path=output_path)


if __name__ == '__main__':
    main()
