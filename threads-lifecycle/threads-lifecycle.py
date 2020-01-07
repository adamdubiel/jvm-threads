# Simple script to merge results of JVM threads lifecycle logging (-Xlog:thread+os)
# with output of jstack.

import argparse
from operator import attrgetter
from parse import (parse, compile)

parser = argparse.ArgumentParser(description='Merge threads lifecycle logs and jstack output')

parser.add_argument('-t', dest='threads_log', required=True, help='path to threads.log file')
parser.add_argument('-s', dest='stack_log', required=True, help='path to stackdump file')
parser.add_argument('-b', dest='print_buckets', required=False, default=True, help='should it print normalized buckets')
parser.add_argument('-b', dest='print_buckets', required=False, default=True, help='should it print normalized buckets')

args = parser.parse_args()

print("Merging thread lifecycle found from: {} with stackdump from: {}".format(args.threads_log, args.stack_log))

def parseThreadsLog(threads_log):
    # [0.019s][info][os,thread] Thread is alive (tid: 23727, pthread id: 139650126874368).
    pattern = compile("[{time}][{level}][{loggers}] Thread {type} (tid: {tid:d}, pthread id: {pthid:d}).")
    time_pattern = compile("{seconds:d}.{millis:d}s")
    threads = {}

    with open(threads_log) as f:
        for line in f:
            parsed = pattern.parse(line)
            if parsed:
                tid = parsed.named['tid']

                if tid not in threads:
                    threads[tid] = []
                events = threads[tid]

                parsed_time = time_pattern.parse(parsed.named['time'])
                time = parsed_time.named['seconds'] * 1000 + parsed_time.named['millis']

                events.append({'time': time, 'type': parsed.named['type'], 'tid': parsed.named['tid']})

    return threads

def parseStackThread(parsed):
    return {'tid': int(parsed.named['hextid'], 16), 'name': parsed.named['name']}

def parseStackLog(stack_log):
    # "pool-3-thread-19" #108 prio=5 os_prio=0 tid=0x00007f0290067000 nid=0x5d30 waiting on condition  [0x00007f026f3b6000]
    app_thread_pattern = compile("\"{name}\" #{} prio={} os_prio={} tid={} nid={hextid} {}  [{}]")
    # "VM Thread" os_prio=0 tid=0x00007f02d017c800 nid=0x5cb6 runnable
    vm_thread_pattern = compile("\"{name}\" os_prio={} tid={} nid={hextid} {}")

    threads = {}

    with open(stack_log) as f:
        for line in f:
            parsed = app_thread_pattern.parse(line)
            if parsed:
                e = parseStackThread(parsed)
                threads[e['tid']] = e
            else:
                parsed = vm_thread_pattern.parse(line)
                if parsed:
                    e = parseStackThread(parsed)
                    threads[e['tid']] = e
    return threads


threadEvents = parseThreadsLog(args.threads_log)
threadNames = parseStackLog(args.stack_log)

events = []
for tid, tevents in threadEvents.items():
    if tid in threadNames:
        name = threadNames[tid]['name']
    else:
        name = 'Could not match'

    for event in tevents:
        events.append({'name': name, 'tid': tid, 'event': event['type'], 'time': event['time']})

events.sort(key=lambda e: e['time'])

def timeBuckets(events):
    window = 100
    endTime = events[-1]['time']

    buckets = []
    for bucket in range(0, endTime, window):
        buckets.append({'windowStart': bucket, 'items': 0})

    for e in events:
        if e['event'] == 'is alive':
            slot = int(e['time'] / 100)
            buckets[slot]['items'] = buckets[slot]['items'] + 1

    counter = 0
    for bucket in buckets:
        counter = counter + bucket['items']
        bucket['items'] = counter

    return buckets

buckets = timeBuckets(events)

for b in buckets:
    print("{}\t{}".format(b['windowStart'], b['items']))

#for e in events:
#    print("{}\t{}\t{}".format(e['time'], e['name'], e['event']))
