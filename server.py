if __name__ == '__main__':
    from example import create_app
    # noinspection PyUnresolvedReferences
    import tests
    bolinette = create_app()
    bolinette.run_command()
