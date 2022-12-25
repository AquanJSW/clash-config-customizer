import argparse


def parse_args(init_args=None):
    parser = argparse.ArgumentParser(
        description="Set environment variable 'https_proxy' if you want to use proxy."
    )

    # Required Options
    required_opts = parser.add_argument_group('Required Options')
    required_opts.add_argument(
        '-s',
        '--subscription-configs',
        help='paths or URLs',
        nargs='+',
        required=True,
    )
    required_opts.add_argument(
        '-p',
        '--prefixes',
        help='proxy name prefixes for each subscription',
        nargs='+',
        required=True,
    )
    required_opts.add_argument(
        '-r',
        '--enable-renames',
        help='rename proxies like "HK-01". Use 1/0 for yes/no',
        nargs='+',
        required=True,
    )
    required_opts.add_argument(
        '-t', '--template-configs', help='paths or URLs', nargs='+', required=True
    )
    required_opts.add_argument(
        '-o',
        '--output-names',
        help='names of output configs (no extension)',
        nargs='+',
        required=True,
    )

    # Standard Options
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args(init_args)

    return args
