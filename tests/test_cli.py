from cli.main import build_parser


def test_cli_parsing():
    parser = build_parser()
    args = parser.parse_args(["fascicolo", "--sanitize", "--profile", "pdua_safe"])
    assert args.input_folder.as_posix() == "fascicolo"
    assert args.sanitize is True
    assert args.profile == "pdua_safe"
