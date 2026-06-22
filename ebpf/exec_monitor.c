// eBPF lifecycle monitor loaded by BCC.
//
// It reports successful process executions and process exits. User space
// correlates both event types and enriches exec events from /proc.

#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

#define TASK_COMM_LEN 16
#define EVENT_EXEC 1
#define EVENT_EXIT 2

struct data_t {
    u32 event_type;
    u32 pid;
    u32 ppid;
    u32 uid;
    s32 exit_status;
    u64 timestamp_ns;
    char comm[TASK_COMM_LEN];
};

BPF_PERF_OUTPUT(events);

static __always_inline void fill_common(struct data_t *data, u32 event_type)
{
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    u64 uid_gid = bpf_get_current_uid_gid();

    data->event_type = event_type;
    data->pid = bpf_get_current_pid_tgid() >> 32;
    data->uid = uid_gid;
    data->timestamp_ns = bpf_ktime_get_ns();
    data->ppid = task->real_parent->tgid;
    bpf_get_current_comm(&data->comm, sizeof(data->comm));
}

TRACEPOINT_PROBE(sched, sched_process_exec)
{
    struct data_t data = {};

    fill_common(&data, EVENT_EXEC);
    events.perf_submit(args, &data, sizeof(data));

    return 0;
}

TRACEPOINT_PROBE(sched, sched_process_exit)
{
    struct data_t data = {};
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    u64 pid_tgid = bpf_get_current_pid_tgid();

    // Ignore worker-thread exits; lifecycle records represent processes.
    if ((u32)pid_tgid != (u32)(pid_tgid >> 32))
        return 0;

    fill_common(&data, EVENT_EXIT);
    data.exit_status = task->exit_code;
    events.perf_submit(args, &data, sizeof(data));

    return 0;
}
