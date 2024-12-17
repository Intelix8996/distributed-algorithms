import argparse


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", "--name", type=str, default="node1", help="node name")
    parser.add_argument(
        "-s", "--state", type=str, default="follower", help="initial node state"
    )

    return parser.parse_args()
