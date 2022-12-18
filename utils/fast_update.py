"""

Args
---
- config: previous output config
- template_config: tiny update like rules update

Function
---
Instantiate a template config and copy proxies in config to it, then override
the old config.
"""
import argparse
import yaml
from utils.utils import load_yaml

parser = argparse.ArgumentParser()
parser.add_argument('config', help='config to be update.')
parser.add_argument('template', help='template to be injected.')


def main():
    # parse args
    args = parser.parse_args()

    # load configs
    config = load_yaml(args.config)
    template = load_yaml(args.template)

    # Template has 2 type of changes to update:
    # 1. proxy
    # 2. non-proxy

    # inject proxies in template to config
    if 'proxies' in template.keys():
        for i in range(len(template['proxies'])):
            for j in range(len(config['proxies'])):
                if template['proxies'][i]['name'] == config['proxies'][j]['name']:
                    config['proxies'][j] = template['proxies'][i]

    # inject injected config proxies to template
    template['proxies'] = config['proxies']

    # save
    with open(args.config, 'w') as fd:
        yaml.safe_dump(template, fd, allow_unicode=True)

    print(f'config updated: {args.config}')


if __name__ == '__main__':
    main()
