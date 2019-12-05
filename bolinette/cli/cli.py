import os
import sys

from bolinette.cli import Parser


def main():
    cwd = os.getcwd()
    Parser(cwd).execute(sys.argv)
