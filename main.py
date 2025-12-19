import sys

from loguru import logger

import visu

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("need the zipped file as an argument")
        exit(1)

    file = sys.argv[1]
    visu.run(file)
