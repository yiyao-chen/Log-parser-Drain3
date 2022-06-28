import json
import logging
import os
import sys
import re
import time
from os.path import dirname

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistence

def main():
    persistence = FilePersistence("drain3_state.bin")
    in_folder = "logs/chaos_logs"
    to_file = "result/chaos_result.txt"

    logger, template_miner = init_config(persistence)
    parse_folder(in_folder, logger, template_miner)
    write_result_to_file(logger, template_miner, to_file)

    print("Prefix Tree:")
    template_miner.drain.print_tree()
    template_miner.profiler.report(0)


def init_config(persistence):
    logger = logging.getLogger(__name__)
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
    config = TemplateMinerConfig()
    config.load(dirname(__file__) + "/drain3.ini")
    config.profiling_enabled = True
    template_miner = TemplateMiner(persistence, config=config)
    return logger, template_miner


def get_lines_from_file(file):
    with open(file) as f:
        lines = f.readlines()
    return lines


def parse_folder(folder, logger, template_miner):
    for file in os.scandir(folder):
        if file.is_file():
            parse_file(file, logger, template_miner)


def parse_file(file, logger, template_miner):
    line_count = 0
    start_time = time.time()
    batch_start_time = start_time
    batch_size = 10000

    lines = get_lines_from_file(file)

    for line in lines:
        line = line.rstrip()
        in_bracket = "\[(.*?)\]"
        line = re.sub(in_bracket, "", line)  # remove brackets and contents inside brackets

        result = template_miner.add_log_message(line)
        line_count += 1
        if line_count % batch_size == 0:
            time_took = time.time() - batch_start_time
            rate = batch_size / time_took
            logger.info(f"Processing line: {line_count}, rate {rate:.1f} lines/sec, "
                        f"{len(template_miner.drain.clusters)} clusters so far.")
            batch_start_time = time.time()
        if result["change_type"] != "none":
            result_json = json.dumps(result)
            logger.info(f"Input ({line_count}): " + line)
            logger.info("Result: " + result_json)

    time_took = time.time() - start_time
    rate = line_count / time_took
    logger.info(
        f"--- Done processing file in {time_took:.2f} sec. Total of {line_count} lines, rate {rate:.1f} lines/sec, "
        f"{len(template_miner.drain.clusters)} clusters")


def write_result_to_file(logger, template_miner, to_file):
    sorted_clusters = sorted(template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
    to_file = open(to_file, "w")
    for cluster in sorted_clusters:
        logger.info(cluster)
        to_file.write(str(cluster) + "\n")
    to_file.close()


if __name__ == '__main__':
    main()
