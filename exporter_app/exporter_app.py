#!/usr/bin/env python
from flask import Flask, Response
from prometheus_client import Gauge, generate_latest
import xml.etree.ElementTree as ET
import os


def passenger_status():

    # Var to indicate successful or failed scrape
    passenger_scrape = 0

    try:
        # Create our results dictionary
        results_dict = {}

        # Query passenger
        passenger_stat = os.popen("/usr/sbin/passenger-status --show=xml 2>/dev/null")
        tree = ET.fromstring(passenger_stat.read())
        # tree = ET.fromstring(xml)

        # Add simple metrics (process count and queue)
        results_dict["process_count"] = tree.findtext("process_count")
        results_dict["queued_requests"] = tree.findtext("get_wait_list_size")

        # Calculate RAM usage
        total_ram_kb = 0
        supergroups = tree.iter("supergroups")

        for supergroup in supergroups:
            for group in supergroup.iter("group"):
                processes_list = group.iter("processes")
                for p in processes_list:
                    processes = p.findall("process")

                    for proc in processes:
                        total_ram_kb += int(proc.findtext("real_memory"))

        results_dict["ram_usage"] = str(total_ram_kb/1024)

        # Set success to 1 and add to dict
        passenger_scrape = 1
        results_dict["passenger_up"] = str(passenger_scrape)

    # Broad exception catch....anything goes wrong return empty data points and passenger_up = 0
    except:
        results_dict = {"passenger_up": str(passenger_scrape),
                        "process_count": 0,
                        "queued_requests": 0,
                        "ram_usage": 0}

    return results_dict


# Define Prometheus metrics
passenger_process_count = Gauge(
    'passenger_nginx_current_processes',
    'Number of passenger process currently running'
)

passenger_request_queue_count = Gauge(
    'passenger_nginx_request_queue',
    'Number of requests queued'
)

passenger_ram_usage = Gauge(
    'passenger_nginx_proc_memory',
    'Total RAM utilization for all Passenger processes in MegaBytes'
)

passenger_up = Gauge(
    'passenger_up',
    'Whether or not we had a successful scrape'
)

# Initiate flask app
app = Flask(__name__)


# Create metrics route
@app.route('/metrics')
def metrics():
    metrics = passenger_status()
    content_type = str('text/plain; version=0.0.4; charset=utf-8')

    # Set our counters
    passenger_request_queue_count.set(metrics['queued_requests'])
    passenger_process_count.set(metrics['process_count'])
    passenger_ram_usage.set(metrics['ram_usage'])
    passenger_up.set(metrics['passenger_up'])

    # Return response
    return Response(generate_latest(), mimetype=content_type)