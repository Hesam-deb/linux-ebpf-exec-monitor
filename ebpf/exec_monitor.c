// eBPF program for Linux eBPF Process Execution Monitor.
//
// This program is loaded by BCC from Python. It attaches to the
// sched:sched_process_exec tracepoint, which fires when a task has
// successfully executed a new program image.

#include <uapi/linux/ptrace.h>

#define TASK_COMM_LEN 16

struct data_t {
    u32 pid;
    u64 timestamp_ns;
    char comm[TASK_COMM_LEN];
};

// Perf buffer used to send events from kernel space to user space.
BPF_PERF_OUTPUT(events);

TRACEPOINT_PROBE(sched, sched_process_exec)
{
    struct data_t data = {};

    // args->pid is provided by the sched_process_exec tracepoint.
    data.pid = args->pid;

    // Kernel monotonic timestamp in nanoseconds.
    data.timestamp_ns = bpf_ktime_get_ns();

    // Current task command name, limited to TASK_COMM_LEN bytes.
    bpf_get_current_comm(&data.comm, sizeof(data.comm));

    // Send the event to the Python loader through the perf buffer.
    events.perf_submit(args, &data, sizeof(data));

    return 0;
}
