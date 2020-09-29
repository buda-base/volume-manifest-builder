#!/usr/bin/env python3
import argparse

# https://docs.python.org/3/library/argparse.html#sub-commands
parent = argparse.ArgumentParser(description='No help',add_help=False)
parent.add_argument('-s', '--something', help='parent help')

children = parent.add_subparsers(title='IOType', description='Pick an IO channel. fs or s3')

fs_parser = children.add_parser('fs', parents=[parent])
fs_parser.add_argument('-e', '--something_else', help='child e help')

children.add_parser('s3', parents=[parent])

frelm = parent.parse_args()

print(frelm)