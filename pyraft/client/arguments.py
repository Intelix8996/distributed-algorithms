import argparse


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", "--name", type=str, default="node1", help="node name")

    return parser.parse_args()
